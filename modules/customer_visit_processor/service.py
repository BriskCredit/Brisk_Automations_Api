from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import TYPE_CHECKING
from utils.logger import get_logger

if TYPE_CHECKING:
    from common.brisk_data_service import BriskDataService

logger = get_logger("app.modules.customer_visit_processor")


class CustomerVisitProcessor:
    """
    A class to process customer visit data for D7, D14, and D21 interactions.
    Fetches all loan data, matches interactions, and generates a combined report.
    """
    
    VISIT_TYPES = {
        7: 'Customer visit, D7',
        14: 'Customer visit, D14',
        21: 'Customer visit, D21'
    }
    
    def __init__(self, data_service: "BriskDataService"):
        """
        Initialize the processor with data service.
        
        Args:
            data_service: BriskDataService for database access
        """
        self._data_service = data_service
        self.d7_loans = None
        self.d14_loans = None
        self.d21_loans = None
        self._report = None
    
    def _enrich_loans(self, loans_df: pd.DataFrame, days: int) -> pd.DataFrame:
        """Enrich loan data with client info, interactions, branches, and staff."""
        if loans_df.empty:
            return pd.DataFrame()
        
        df = loans_df.copy()
        
        # Merge with clients
        df = df.merge(self._data_service.clients, left_on='client_idno', right_on='idno', how='left')
        
        # Get and merge interactions
        interaction_type = self.VISIT_TYPES.get(days, f'Customer visit, D{days}')
        interactions = self._data_service.get_todays_interactions(interaction_type)
        df = df.merge(interactions, left_on='id', right_on='client', how='left')
        
        # Merge with branches
        df = df.merge(
            self._data_service.branches, 
            left_on='branch', 
            right_on='id', 
            how='left'
        ).rename(columns={'branch_x': 'branch_id', 'branch_y': 'branch_name'})
        
        # Merge with staff
        df = df.merge(
            self._data_service.staff, 
            left_on="loan_officer", 
            right_on="id", 
            how="left"
        ).rename(columns={'name': 'loan_officer_name'})
        
        # Clean up columns
        columns_to_drop = ['id_y', 'client_y', 'branch_id', 'loan_officer', 'id', 'idno']
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        df = df.drop(columns=existing_columns)
        
        # Rename columns
        rename_map = {'id_x': 'client_id', 'client_x': 'client_name'}
        existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=existing_renames)
        
        # Remove duplicates and fill NA
        if 'client_id' in df.columns and 'client_idno' in df.columns:
            df = df.drop_duplicates(subset=['client_id', 'client_idno'])
        df = df.fillna({'type': 'No Visit'})
        
        return df
    
    def _generate_branch_report(self, df: pd.DataFrame, days: int) -> tuple:
        """
        Generate a visit report grouped by branch for a specific day interval.
        
        Returns:
            tuple: (report DataFrame, total_visited, total_loans)
        """
        if df.empty:
            return pd.DataFrame(columns=['Branch', f'D{days} Visits']), 0, 0
        
        interaction_type = self.VISIT_TYPES.get(days, f'Customer visit, D{days}')
        
        report = df.groupby('branch_name').agg(
            total_loans=('client_idno', 'count'),
            visited=('type', lambda x: (x == interaction_type).sum())
        ).reset_index()
        
        # Calculate totals before formatting
        total_visited = int(report['visited'].sum())
        total_loans = int(report['total_loans'].sum())
        
        report['visit_rate'] = (report['visited'] / report['total_loans'] * 100).round(1)
        report[f'D{days} Visits'] = report.apply(
            lambda row: f"{int(row['visited'])}/{int(row['total_loans'])} ({row['visit_rate']}%)", 
            axis=1
        )
        
        return report[['branch_name', f'D{days} Visits']].rename(columns={'branch_name': 'Branch'}), total_visited, total_loans
    
    def process(self) -> pd.DataFrame:
        """
        Process all D7, D14, and D21 data and return a combined report.
        
        Returns:
            DataFrame with columns: Branch, D7 Visits, D14 Visits, D21 Visits
            Includes a TOTAL row at the bottom.
        """
        reports = {}
        all_loans = {}
        totals = {}  # Store totals for each interval
        
        # Fetch and process each day interval
        for days in [7, 14, 21]:
            key = f'D{days}'
            logger.info(f"Fetching {key} loans...")
            
            # Get loans and enrich
            loans = self._data_service.get_loans_by_days_ago(days)
            logger.info(f"  Found {len(loans)} loans disbursed {days} days ago")
            
            enriched = self._enrich_loans(loans, days)
            all_loans[key] = enriched
            
            # Generate branch report (now returns tuple with totals)
            report_df, visited, total = self._generate_branch_report(enriched, days)
            reports[key] = report_df
            totals[key] = {'visited': visited, 'total': total}
        
        # Combine all reports into one
        logger.info("Combining reports...")
        combined = reports['D7'].copy()
        
        for days in [14, 21]:
            key = f'D{days}'
            combined = combined.merge(
                reports[key],
                on='Branch',
                how='outer'
            )
        
        # Fill missing values and sort
        combined = combined.fillna('0/0 (0.0%)')
        combined = combined.sort_values('Branch').reset_index(drop=True)
        
        # Create totals row
        totals_row = {'Branch': 'TOTAL'}
        for days in [7, 14, 21]:
            key = f'D{days}'
            visited = totals[key]['visited']
            total = totals[key]['total']
            rate = round(visited / total * 100, 1) if total > 0 else 0.0
            totals_row[f'{key} Visits'] = f"{visited}/{total} ({rate}%)"
        
        # Append totals row
        combined = pd.concat([combined, pd.DataFrame([totals_row])], ignore_index=True)
        
        # Store individual loan DataFrames as attributes for access if needed
        self.d7_loans = all_loans['D7']
        self.d14_loans = all_loans['D14']
        self.d21_loans = all_loans['D21']
        self._report = combined
        
        logger.info("Customer visit processing complete!")
        return combined
    

    def to_excel(self) -> str:
        """
        Export the report to a styled Excel file using xlsxwriter.
        Filename is generated dynamically based on current date.
            
        Returns:
            Path to the saved file
        """
        if self._report is None:
            raise ValueError("No report available. Call process() first.")
        
        # Generate dynamic filename: customer_visits_report_march_02.xlsx
        today = datetime.now()
        temp_dir = Path("uploads/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = temp_dir / f"customer_visits_report_{today.strftime('%B_%d').lower()}.xlsx"
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Write data starting at row 2 (leave row 1 for title)
            self._report.to_excel(writer, sheet_name='Visits Report', index=False, startrow=2)
            
            workbook = writer.book
            worksheet = writer.sheets['Visits Report']
            
            # Define formats
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'font_color': '#1E88E5',
                'align': 'left'
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1E88E5',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            })
            
            branch_format = workbook.add_format({
                'bg_color': '#E3F2FD',
                'border': 1,
                'align': 'left',
                'valign': 'vcenter'
            })
            
            branch_total_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1E88E5',
                'font_color': 'white',
                'border': 1,
                'align': 'left',
                'valign': 'vcenter'
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            total_row_format = workbook.add_format({
                'bold': True,
                'bg_color': '#BBDEFB',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Add title
            today = datetime.now().strftime('%B %d, %Y')
            worksheet.write(0, 0, f'Customer Visits Report - {today}', title_format)
            
            # Write headers with format
            for col_num, col_name in enumerate(self._report.columns):
                worksheet.write(2, col_num, col_name, header_format)
            
            # Write data with formatting
            for row_num, row_data in enumerate(self._report.values):
                is_total_row = row_data[0] == 'TOTAL'
                
                for col_num, value in enumerate(row_data):
                    if col_num == 0:  # Branch column
                        if is_total_row:
                            worksheet.write(row_num + 3, col_num, value, branch_total_format)
                        else:
                            worksheet.write(row_num + 3, col_num, value, branch_format)
                    else:  # Data columns
                        if is_total_row:
                            worksheet.write(row_num + 3, col_num, value, total_row_format)
                        else:
                            worksheet.write(row_num + 3, col_num, value, cell_format)
            
            # Set column widths
            worksheet.set_column('A:A', 22)  # Branch column
            worksheet.set_column('B:D', 18)  # Data columns
            
            # Set row height for header
            worksheet.set_row(2, 25)
        
        logger.info(f"Report saved to: {filename}")
        return str(filename)
