from datetime import datetime
import pandas as pd
from typing import TYPE_CHECKING, Optional, Dict
from utils.logger import get_logger

if TYPE_CHECKING:
    from common.brisk_data_service import BriskDataService

logger = get_logger("app.modules.customer_calls")


class CustomerCallsProcessor:
    """
    Process call dialer data for loans disbursed at different intervals.
    Generates a combined report for 7, 30, 60, and 90 days.
    """
    
    DAY_INTERVALS = [7, 30, 60, 90]
    
    # Column name mapping: days -> display name
    COLUMN_NAMES = {
        7: 'D7',
        30: 'D30',
        60: 'DD+30',
        90: 'DD+60'
    }
    
    def __init__(self, data_service: "BriskDataService"):
        """
        Initialize the processor with data service.
        
        Args:
            data_service: BriskDataService for database access
        """
        self._data_service = data_service
        self._report: Optional[pd.DataFrame] = None
        self.loans_data: Dict[str, pd.DataFrame] = {}  # Store individual loan DataFrames
    
    def _enrich_loans(self, loans_df: pd.DataFrame, interactions: pd.DataFrame) -> pd.DataFrame:
        """Enrich loans with clients, interactions, branches, and staff."""
        if loans_df.empty:
            return pd.DataFrame()
        
        df = loans_df.copy()
        
        # Merge with clients (adds client 'id' column)
        df = df.merge(
            self._data_service.clients, 
            left_on='client_idno', 
            right_on='idno', 
            how='left',
            suffixes=('', '_client')
        )
        
        # Merge with interactions using client id
        df = df.merge(
            interactions, 
            left_on='id', 
            right_on='client', 
            how='left',
            suffixes=('', '_interaction')
        )
        
        # Merge with branches
        df = df.merge(
            self._data_service.branches,
            left_on='branch',
            right_on='id',
            how='left',
            suffixes=('', '_branch')
        ).rename(columns={'branch': 'branch_id', 'branch_branch': 'branch_name'})
        
        # Merge with staff to get loan officer name
        df = df.merge(
            self._data_service.staff,
            left_on='loan_officer',
            right_on='id',
            how='left',
            suffixes=('', '_staff')
        ).rename(columns={'name': 'loan_officer_name'})
        
        return df
    
    def _generate_branch_report(self, df: pd.DataFrame, days: int) -> tuple:
        """Generate called/total report by branch. Only includes loans with balance > 0."""
        col_name = self.COLUMN_NAMES.get(days, f'D{days}')
        
        if df.empty:
            return pd.DataFrame(columns=['Branch', col_name]), 0, 0
        
        # Filter only loans with balance > 0 for the summary
        df_active = df[df['balance'] > 0].copy()
        
        if df_active.empty:
            return pd.DataFrame(columns=['Branch', col_name]), 0, 0
        
        report = df_active.groupby('branch_name').agg(
            total_loans=('loan_id', 'count'),
            called=('type', lambda x: x.notna().sum())
        ).reset_index()
        
        total_called = int(report['called'].sum())
        total_loans = int(report['total_loans'].sum())
        
        report['call_rate'] = (report['called'] / report['total_loans'] * 100).round(1)
        report[col_name] = report.apply(
            lambda row: f"{int(row['called'])}/{int(row['total_loans'])} ({row['call_rate']}%)",
            axis=1
        )
        
        return report[['branch_name', col_name]].rename(columns={'branch_name': 'Branch'}), total_called, total_loans
    
    def process(self) -> pd.DataFrame:
        """
        Process all intervals and return combined report.
        
        Returns:
            DataFrame with columns: Branch, D7, D30, DD+30, DD+60
            Includes a TOTAL row at the bottom.
        """
        reports = {}
        totals = {}
        
        for days in self.DAY_INTERVALS:
            col_name = self.COLUMN_NAMES.get(days, f'D{days}')
            logger.info(f"Fetching {col_name} loans ({days} days ago)...")
            
            # Get loans
            loans = self._data_service.get_loans_by_days_ago(days)
            logger.info(f"  Found {len(loans)} loans disbursed {days} days ago")
            
            # Get interactions from day after disbursement
            interactions = self._data_service.get_call_dialer_interactions_by_days(days)
            logger.info(f"  Found {len(interactions)} call dialer interactions (from {days-1} days ago)")
            
            # Enrich with interval-specific interactions
            enriched = self._enrich_loans(loans, interactions)
            self.loans_data[col_name] = enriched
            
            # Generate report
            report_df, called, total = self._generate_branch_report(enriched, days)
            reports[days] = report_df
            totals[days] = {'called': called, 'total': total}
        
        # Combine all reports
        logger.info("Combining reports...")
        combined = reports[7].copy()
        
        for days in [30, 60, 90]:
            combined = combined.merge(reports[days], on='Branch', how='outer')
        
        # Fill missing and sort
        combined = combined.fillna('')
        combined = combined.sort_values('Branch').reset_index(drop=True)
        
        # Create totals row
        totals_row = {'Branch': 'TOTAL'}
        for days in self.DAY_INTERVALS:
            col_name = self.COLUMN_NAMES.get(days, f'D{days}')
            called = totals[days]['called']
            total = totals[days]['total']
            if total == 0:
                totals_row[col_name] = ''
            else:
                rate = round(called / total * 100, 1)
                totals_row[col_name] = f"{called}/{total} ({rate}%)"
        
        combined = pd.concat([combined, pd.DataFrame([totals_row])], ignore_index=True)
        self._report = combined
        
        logger.info("Customer calls processing complete!")
        return combined
    
    def to_excel(self) -> str:
        """
        Export the report to a styled Excel file using xlsxwriter.
        Includes summary sheet and detailed sheets for each category.
        
        Returns:
            Path to the saved file
        """
        if self._report is None:
            raise ValueError("No report available. Call process() first.")
        
        # Generate dynamic filename
        today = datetime.now()
        filename = f"call_dialer_report_{today.strftime('%B_%d').lower()}.xlsx"
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            workbook = writer.book
            
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
            
            # ===== SUMMARY SHEET =====
            self._report.to_excel(writer, sheet_name='Summary', index=False, startrow=2)
            worksheet = writer.sheets['Summary']
            
            report_date = datetime.now().strftime('%B %d, %Y')
            worksheet.write(0, 0, f'Call Dialer Report - {report_date}', title_format)
            
            for col_num, col_name in enumerate(self._report.columns):
                worksheet.write(2, col_num, col_name, header_format)
            
            for row_num, row_data in enumerate(self._report.values):
                is_total_row = row_data[0] == 'TOTAL'
                for col_num, value in enumerate(row_data):
                    if col_num == 0:
                        fmt = branch_total_format if is_total_row else branch_format
                    else:
                        fmt = total_row_format if is_total_row else cell_format
                    worksheet.write(row_num + 3, col_num, value, fmt)
            
            worksheet.set_column('A:A', 22)
            worksheet.set_column('B:E', 18)
            worksheet.set_row(2, 25)
            
            # ===== DETAILED SHEETS FOR EACH CATEGORY =====
            for col_name, df in self.loans_data.items():
                if df.empty:
                    continue
                
                # Prepare detailed data - only NOT CALLED accounts with balance > 0
                detail_df = df.copy()
                detail_df = detail_df[(detail_df['type'].isna()) & (detail_df['balance'] > 0)]
                
                if detail_df.empty:
                    continue
                
                # Convert timestamps to readable dates
                detail_df['disbursement_date'] = pd.to_datetime(detail_df['disbursement'], unit='s')
                detail_df['interaction_time'] = pd.to_datetime(detail_df['time'], unit='s')
                
                # Select and rename columns for output
                detail_columns_filtered = [
                    'loan_id', 'client_idno', 'branch_name', 'loan_officer_name',
                    'amount', 'balance', 'disbursement_date'
                ]
                available_cols = [c for c in detail_columns_filtered if c in detail_df.columns]
                detail_df = detail_df[available_cols]
                
                # Rename columns for display
                column_rename = {
                    'loan_id': 'Loan ID',
                    'client_idno': 'Client ID',
                    'branch_name': 'Branch',
                    'loan_officer_name': 'Loan Officer',
                    'amount': 'Amount',
                    'balance': 'Balance',
                    'disbursement_date': 'Disbursement Date'
                }
                detail_df = detail_df.rename(columns=column_rename)
                
                # Write to sheet
                sheet_name = f'{col_name} Not Called'
                detail_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)
                
                ws = writer.sheets[sheet_name]
                ws.write(0, 0, f'{col_name} Not Called - {report_date} ({len(detail_df)} accounts)', title_format)
                
                # Format headers
                for col_num, col_label in enumerate(detail_df.columns):
                    ws.write(2, col_num, col_label, header_format)
                
                # Set column widths
                ws.set_column('A:A', 12)  # Loan ID
                ws.set_column('B:B', 15)  # Client ID
                ws.set_column('C:C', 18)  # Branch
                ws.set_column('D:D', 20)  # Loan Officer
                ws.set_column('E:F', 12)  # Amount, Balance
                ws.set_column('G:G', 20)  # Disbursement Date
                ws.set_row(2, 25)
        
        logger.info(f"Report saved to: {filename}")
        return filename
