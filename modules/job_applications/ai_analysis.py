import os
import json
from typing import Optional, Tuple
from dataclasses import dataclass
from utils.logger import get_logger
import re

logger = get_logger("app.modules.job_applications.ai_analysis")


@dataclass
class AnalysisResult:
    """Result of AI CV analysis."""
    score: float  # 0-10
    comments: str
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str


class AIAnalysisService:
    """
    Service for AI-powered CV/Resume analysis against job descriptions.
    Uses OpenAI GPT models for analysis.
    
    The analysis takes into account:
    1. Job Description (summary, requirements, responsibilities, qualifications)
    2. Custom Instructions from admin (given PRIORITY)
    3. Extracted resume text
    """
    
    def __init__(self):
        """Initialize the AI analysis service."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. AI analysis will not be available.")
        
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
        return self._client
    
    def is_available(self) -> bool:
        """Check if AI analysis is available."""
        return self.api_key is not None and self.client is not None
    
    def analyze_cv(
        self,
        resume_text: str,
        job_title: str,
        job_summary: Optional[str] = None,
        job_requirements: Optional[str] = None,
        job_responsibilities: Optional[str] = None,
        job_qualifications: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Tuple[Optional[AnalysisResult], Optional[str]]:
        """
        Analyze a CV/resume against a job description.
        
        Args:
            resume_text: Extracted text from the resume
            job_title: Title of the job position
            job_summary: Job summary/overview
            job_requirements: Required qualifications
            job_responsibilities: Job responsibilities
            job_qualifications: Preferred qualifications
            custom_instructions: Admin's custom instructions (PRIORITY)
            
        Returns:
            Tuple of (AnalysisResult, error_message)
            Returns (None, error) if analysis fails
        """
        if not self.is_available():
            return None, "AI analysis service not available. Check OPENAI_API_KEY."
        
        if not resume_text or len(resume_text.strip()) < 50:
            return None, "Resume text is too short for analysis"
        
        # Build the job description context
        jd_parts = [f"**Job Title:** {job_title}"]
        
        if job_summary:
            jd_parts.append(f"\n**Summary:**\n{job_summary}")
        
        if job_requirements:
            jd_parts.append(f"\n**Requirements:**\n{job_requirements}")
        
        if job_responsibilities:
            jd_parts.append(f"\n**Responsibilities:**\n{job_responsibilities}")
        
        if job_qualifications:
            jd_parts.append(f"\n**Preferred Qualifications:**\n{job_qualifications}")
        
        job_description = "\n".join(jd_parts)
        
        # Build the system prompt
        system_prompt = self._build_system_prompt(custom_instructions)
        
        # Build the user prompt
        user_prompt = self._build_user_prompt(job_description, resume_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Parse the response
            result = self._parse_response(content)
            
            if result:
                logger.info(f"AI analysis completed. Score: {result.score}/10")
                return result, None
            else:
                return None, "Failed to parse AI response"
            
        except Exception as e:
            error_msg = f"AI analysis failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def _build_system_prompt(self, custom_instructions: Optional[str] = None) -> str:
        """Build the system prompt for the AI model."""
        base_prompt = """You are a strict HR recruiter evaluating candidates. Analyze the resume against the job description with emphasis on DIRECT JOB FIT.

**Scoring Rules (Be Strict):**
- 9-10: Perfect match. Exceeds ALL requirements with directly relevant experience.
- 7-8: Strong match. Meets all core requirements, minor gaps acceptable.
- 5-6: Partial match. Meets some requirements but has notable gaps.
- 3-4: Weak match. Missing key requirements, would need significant training.
- 0-2: Poor fit. Does not meet basic requirements for the role.

**Analysis Guidelines:**
- Prioritize direct, relevant experience over transferable skills
- Penalize missing must-have requirements
- Keep comments concise (2-3 sentences max)
- List only the most relevant strengths/weaknesses (max 5 each)
- Recommendation must be 2 sentences or less"""

        if custom_instructions:
            base_prompt += f"""

**PRIORITY INSTRUCTIONS FROM HIRING MANAGER:**
{custom_instructions}

Apply these instructions strictly. They override default criteria."""

        base_prompt += """

Respond ONLY with this JSON (no other text):
{
    "score": <number 0-10>,
    "comments": "<2-3 sentence analysis>",
    "strengths": ["<max 5 items>"],
    "weaknesses": ["<max 5 items>"],
    "recommendation": "<2 sentences max>"
}"""

        return base_prompt
    
    def _build_user_prompt(self, job_description: str, resume_text: str) -> str:
        """Build the user prompt with job description and resume."""
        return f"""Please analyze the following candidate's resume against the job description.

## JOB DESCRIPTION:
{job_description}

## CANDIDATE'S RESUME:
{resume_text}

Provide your analysis in the specified JSON format."""
    
    def _parse_response(self, content: str) -> Optional[AnalysisResult]:
        """Parse the AI response into an AnalysisResult."""
        try:
            # Try to extract JSON from the response
            # Handle cases where the model wraps JSON in markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            data = json.loads(content)
            
            score = float(data.get("score", 0))
            score = max(0, min(10, score))  # Clamp to 0-10
            
            # Enforce max 5 strengths/weaknesses
            strengths = data.get("strengths", [])[:5]
            weaknesses = data.get("weaknesses", [])[:5]
            
            return AnalysisResult(
                score=score,
                comments=data.get("comments", ""),
                strengths=strengths,
                weaknesses=weaknesses,
                recommendation=data.get("recommendation", "")
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response content: {content[:500]}")
            
            # Try to extract score and comments manually as fallback
            try:
                score_match = re.search(r'"score"\s*:\s*(\d+\.?\d*)', content)
                if score_match:
                    score = float(score_match.group(1))
                    return AnalysisResult(
                        score=score,
                        comments=content,  # Use full content as comments
                        strengths=[],
                        weaknesses=[],
                        recommendation=""
                    )
            except:
                pass
            
            return None
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return None
    
    def format_analysis_for_display(self, result: AnalysisResult) -> str:
        """
        Format analysis result for display/storage.
        
        Args:
            result: AnalysisResult object
            
        Returns:
            Formatted string for display
        """
        lines = [
            f"## Score: {result.score}/10",
            "",
            "### Analysis",
            result.comments,
            "",
            "### Strengths",
        ]
        
        for strength in result.strengths:
            lines.append(f"- {strength}")
        
        lines.append("")
        lines.append("### Weaknesses/Gaps")
        
        for weakness in result.weaknesses:
            lines.append(f"- {weakness}")
        
        lines.append("")
        lines.append("### Recommendation")
        lines.append(result.recommendation)
        
        return "\n".join(lines)
