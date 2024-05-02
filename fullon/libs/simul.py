"""
description
"""

import pandas as pd
from libs import log
from PIL import Image
import numpy as np
from tabulate import tabulate
from typing import List, Dict, Union, Any, Optional
from termcolor import cprint, colored

logger = log.fullon_logger(__name__)


class simul:
    """description"""

    def __init__(self):
        """description"""
        pass

    def __del__(self):
        """description"""
        pass

    def plot(self, df):
        """description"""
        pass

    @staticmethod
    def consolidate_results(df: pd.DataFrame) -> pd.DataFrame:
        """
        Consolidates results from sub-strategies into a single summary row.

        Args:
        df (DataFrame): The DataFrame containing the sub-strategy results.

        Returns:
        DataFrame: A DataFrame containing the consolidated results.
        """
        # Dictionary to hold our consolidated results
        interest_earned = df.iloc[-1]['Stake Yield']
        ending_cash = df.iloc[-1]['Ending Cash']
        profit = df['Profit'].sum()+interest_earned
        starting_cash = ending_cash - profit
        roi = (ending_cash - starting_cash)/starting_cash
        consolidated = {
            'TTrades': df['TTrades'].sum(),  # Assuming total trades is an integer count
            'Win rate %': round(df['Win rate %'].mean(), 2),
            'Fees': round(df['Fees'].sum(), 2),
            'Stake Yield': round(interest_earned, 2),
            'Trade Profit': round(df['Profit'].sum(), 2),
            'Total Profit': round(profit, 2),
            'ROI': round(roi*100, 2),
            'Ending Cash': ending_cash,
            'AvgReturn': round(df['AvgReturn'].mean(), 2),
            'MedReturn': round(df['MedReturn'].mean(), 2),
            'NegStdDev': round(df['NegStdDev'].max(), 2),
            'PosStdDev': round(df['PosStdDev'].max(), 2),
            'Max Drawdown %': round(df['Max Drawdown %'].max(), 2),
            'SharpeRatio': round(df['SharpeRatio'].mean(), 2)
        }
        # Convert the dictionary to a DataFrame
        consolidated_df = pd.DataFrame([consolidated])
        return consolidated_df

    def echo_results(self, bot: dict, results: dict, sharpe_filter: float = 0.0,
                     montecarlo: bool = False, visual: bool = False,
                     xls: bool = False, verbose: bool = False):
        """
        Processes the simulation results for output based on given filters.
        Args:
            results (dict): A dictionary of tuples containing bot configurations and their corresponding simulation results.
            sharpe_filter (float): Sharpe ratio filter for the results.
            short (bool): A flag for whether to shorten the output.
        """
        consolidate = len(results) > 1
        df_list = []  # List of dataframes to hold each row of the DataFrame

        for str_id, result in results.items():
            # Process each result and get the DataFrame
            data_for_df = []  # List to hold each row of the DataFrame
            res = self.echo_result(bot=bot, results=result, sharpe_filter=sharpe_filter, montecarlo=montecarlo, xls=xls, verbose=verbose)
            if res is not None and not res.empty:
                # Iterate over each row in the returned DataFrame
                for _, row in res.iterrows():
                    # Create a dictionary for the DataFrame row
                    data_row = {
                        'TTrades': row['TTrades'],
                        'Win rate %': row['Win rate %'],
                        'Fees': row['Fees'],
                        'Stake Yield': row['Stake Yield'],
                        'Profit': row['Profit'],
                        'ROI': row['ROI'],
                        'Ending Cash': row['Ending Cash'],
                        'AvgReturn': row['AvgReturn'],
                        'MedReturn': row['MedReturn'],
                        'NegStdDev': row['NegStdDev'],
                        'PosStdDev': row['PosStdDev'],
                        'Max Drawdown %': row['Max Drawdown %'],
                        'SharpeRatio': row['SharpeRatio']
                    }
                    data_for_df.append(data_row)
            else:
                print("Empty or None DataFrame received for:", str_id)

            # Convert list of dictionaries to DataFrame
            if data_for_df:
                df_list.append(pd.DataFrame(data_for_df))

        # Determine the number of rows in the DataFrames
        # Create a list to hold the new DataFrames
        final_dfs = []

        if consolidate and df_list:
            # Loop over each row index
            for i in range(len(df_list[0])):
                rows = [df.iloc[i] for df in df_list]
                new_df = pd.concat(rows, axis=1).transpose()
                new_df.reset_index(drop=True, inplace=True)
                final_dfs.append(self.consolidate_results(df=new_df))
            final_df = pd.concat(final_dfs, ignore_index=True)
            # Print consolidated results
            cprint('-' * 80, 'cyan')
            cprint('Consolidated results', 'cyan')
            cprint('-' * 80, 'cyan')
            print(tabulate(final_df, headers='keys', tablefmt='pretty', showindex=True))
            # Call the new summary method
            if montecarlo:
                summary_df = self.summarize_simulations(final_df)
                cprint('Statistical Summary of Simulations', 'green')
                print(tabulate(summary_df, headers='keys', tablefmt='pretty', showindex=True))

    def summarize_simulations(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Summarizes the simulation results by providing statistical analysis across all simulations.

        Args:
        df (DataFrame): The DataFrame containing consolidated results from multiple simulations.

        Returns:
        DataFrame: A DataFrame containing the summary statistics of the simulations.
        """
        # Define the statistics to calculate
        summary_df = df.agg(['mean', 'median', 'std', 'min', 'max', 'count'])
        # Transpose for better readability
        summary_df = summary_df.transpose()
        # Formatting the DataFrame for better display
        summary_df = summary_df.round(2)  # Round off to 2 decimal places
        summary_df['count'] = summary_df['count'].astype(int)  # Ensure count is an integer
        return summary_df

    def prepare_data(self, bot, results, sharpe_filter, verbose, xls):
        """
        """
        _results = []
        for bot, result in results:
            # Parse simulation results according to bot's configuration
            summaries = self.parse(results=result, sharpe_filter=sharpe_filter)
            if summaries:
                summary = self.calculate_final_summary(summaries=summaries)
                if summary:
                    _results.append((result, summary))
        _results = sorted(_results, key=lambda x: x[1]['Total Return'], reverse=True)
        if not _results:
            print("No trades, for any simulation apparently")
            return False, False
        transformed_data = []
        for result, summary in _results:
            self.verbose(dfs=summary['df'], verbose=verbose, xls=xls) if verbose or xls else None
            row = {**summary['params'], 'TP': summary['take_profit'], 'SL': summary['stop_loss'], 'TS': summary['trailing_stop'],
                   'TO': summary['timeout'],
                   'TTrades': summary['Total Trades'],
                   'Win rate %': summary['Win Rate (%)'],
                   'Fees': summary['Total Fees'],
                   'Stake Yield': summary['Yield'],
                   'Profit': summary['Total Return'],
                   'ROI': summary['Total ROI %'],
                   'Ending Cash': summary['Ending Cash'],
                   'AvgReturn': summary['Average Return %'],
                   'Duration': summary['Average Duration (hours)'],
                   'MedReturn': summary['Median Return'],
                   'NegStdDev': summary['Negative Returns Standard Deviation'],
                   'PosStdDev': summary['Positive Returns Standard Deviation'],
                   'Max Drawdown %': summary['Max Drawdown %'],
                   'SharpeRatio': summary['Sharpe Ratio']}
            transformed_data.append(row)
        return (_results, transformed_data)

    def echo_result(self,
                    bot: dict,
                    results: list,
                    sharpe_filter: float = 0.0,
                    montecarlo: bool = False,
                    verbose: bool = False,
                    xls: bool = False) -> Optional[pd.DataFrame]:
        """
         Processes the simulation results for output based on given filters.
        Args:
            results (list): A list of tuples containing bot configurations and their corresponding simulation results.
            sharpe_filter (float): Sharpe ratio filter for the results.
            short (bool): A flag for whether to shorten the output.
        Note:
            This function creates an instance of the 'simul' class to parse results and deletes it afterwards.
        """
        try:
            if not results[0][1]:
                print("Simulation produced no results, maybe a problem with your parameters")
                return
        except IndexError:
            print("Simulation produced no results, maybe a problem with your parameters")
            return

        _results, prepared_data = self.prepare_data(bot=bot, results=results,
                                                    sharpe_filter=sharpe_filter,
                                                    xls=xls, verbose=verbose)
        if not _results:
            return

        # Creating the DataFrame
        res_df = pd.DataFrame(prepared_data)
        drop = ['size_currency', 'leverage', 'timeout', 'take_profit', 'stop_loss', 'trailing_stop']
        columns_to_drop = [col for col in drop if col in res_df.columns]
        res_df = res_df.drop(columns_to_drop, axis=1)
        res_df = res_df.sort_values(by='Profit', ascending=False)
        res_df = res_df.loc[:, res_df.iloc[0].notna()]
        symbol = _results[0][1]['Symbol']
        compression = _results[0][1]['Compression']
        period = _results[0][1]['Period']
        strategy = _results[0][1]['Strategy']
        start_date = _results[0][1]['Start Date']
        end_date = _results[0][1]['End Date']
        title = f"Bot: {colored(bot['bot_id'], 'green')} - "
        title += f"Strategy: {colored(strategy, 'green')} - "
        title += f"Symbol: {colored(symbol, 'green')} - "
        title += f"Periods: ({colored(period, 'green')}) - "
        title += f"Compressions: ({colored(compression, 'green')}) - "
        title += f"From: {colored(start_date, 'green')} to {colored(end_date, 'green')}"
        # Styling the print statement
        cprint('-' * 80, 'cyan')
        cprint(title, 'cyan')
        cprint('-' * 80, 'cyan')
        print(tabulate(res_df, headers='keys', tablefmt='pretty', showindex=True))
        if montecarlo:
            montecarlo_df = self._montecarlo(res_df=res_df)
            cprint('-' * 80, 'cyan')
            cprint(f"{colored('Multiple sim results:', 'cyan')} - {title}")
            print(tabulate(montecarlo_df, headers='keys', tablefmt='pretty'))
            cprint('-' * 80, 'cyan')
        return res_df

    def _montecarlo(self, res_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform simulation results res_df into a new DataFrame with only Monte Carlo relevant results.
        Parameters:
            res_df (pd.DataFrame): The DataFrame containing the simulation results.
        Returns:
            pd.DataFrame: A DataFrame containing aggregated statistics for Monte Carlo simulations.
        """
        # Identifying the parameter columns (excluding the performance metrics columns)
        param_cols = [col for col in res_df.columns if col not in ['TTrades', 'Win rate %', 'Stake Yield', 'Ending Cash', 'Fees', 'Profit', 'ROI', 'AvgReturn', 'Duration', 'MedReturn', 'NegStdDev', 'PosStdDev', 'Max Drawdown %', 'SharpeRatio']]
        # Grouping by the unique combinations of simulation parameters
        params_len = len(param_cols)
        grouped = res_df.groupby(param_cols)
        # Calculating the required statistics
        monte_stats = grouped.agg({
            'Profit': ['mean', 'median', 'max', 'min', 'std', 'count'],
        })
        # Flattening the MultiIndex and renaming columns for clarity
        monte_stats.columns = ['_'.join(col).strip() for col in monte_stats.columns.values]
        monte_stats.reset_index(inplace=True)
        # Renaming the aggregated columns
        columns = {'Profit_mean': 'Profit_mean',
                   'Profit_median': 'Profit_median',
                   'Profit_max': 'Profit_max',
                   'Profit_min': 'Profit_min',
                   'Profit_std': 'Profit_std',
                   'Profit_count': 'Count'}

        monte_stats.rename(columns=columns, inplace=True)
        monte_stats['Profit_range'] = monte_stats['Profit_max'] - monte_stats['Profit_min']
        monte_stats['Profit_variance'] = monte_stats['Profit_std'] ** 2
        # Calculating a new risk score
        monte_stats['Risk_Score'] = monte_stats['Profit_std'] / monte_stats['Profit_mean']
        # Ensure that the risk score is a positive number
        monte_stats['Risk_Score'] = monte_stats['Risk_Score'].abs()
        #dynamic_cols = res_df.columns.tolist()[:res_df.columns.get_loc('TO')+1]
        dynamic_cols = res_df.iloc[:, :params_len].columns.tolist()
        # Constructing the new column order
        columns_order = dynamic_cols + ['Count', 'Profit_mean', 'Profit_median', 'Profit_max', 'Profit_min', 'Profit_std', 'Risk_Score']  # Adjusted 'Simulation Count' to 'Simulation_count' and 'Risk Score' to 'Risk_Score'
        monte_stats = monte_stats[columns_order]
        # Rounding profit columns and Risk Score to two decimal places
        stats_cols = ['Profit_mean', 'Profit_median', 'Profit_max', 'Profit_min', 'Profit_std', 'Risk_Score']  # Adjusted 'Risk Score' to 'Risk_Score'
        monte_stats[stats_cols] = monte_stats[stats_cols].round(2)
        # Sorting by average profit in descending order
        monte_stats_sorted = monte_stats.sort_values(by='Profit_mean', ascending=False)
        return monte_stats_sorted  # Return the sorted DataFrame

    def verbose(self, dfs, verbose, xls):
        """description"""
        for feed, df in enumerate(dfs):
            if len(df) > 0:
                # Define desired column order, leave out columns that might not always be present
                column_order = ['num', 'seq', 'side', 'event_price', 'avg_price',
                                'event_size', 'avg_size', 'cost', 'fee', 'pnl', 'pnlfee',
                                'roi', 'timestamp', 'assets', 'reason']
                # Append new columns to the end of the list
                for col in df.columns:
                    if col not in column_order:
                        column_order.append(col)

                # Reorder the columns
                df = df[column_order]
                # Convert the 'assets' column to string and replace NaN with empty string
                df['assets'] = df['assets'].astype(str).replace('nan', '')
                # Replace NaN values with an empty string in the 'reason' column
                df['reason'] = df['reason'].fillna('')
                if verbose:
                    print(df.to_string())
                if xls:
                    str_id = 1
                    filename = f"results_str_{str_id}_feed_{feed}.xls"
                    df.to_excel(filename, engine='openpyxl')

    def parse(self,
              results: List[Union[str, List[Dict[str, Any]]]],
              sharpe_filter: float = 0.0) -> Dict[int, Dict[str, Any]]:
        """
        Parse the results of multiple simulations and calculate various performance metrics.

        Parameters
        ----------
        results : list
            A list of simulation results, where each result is either an error message (str) or a list of trade data (dict).
        bot : dict
            A dictionary containing various bot settings, such as verbosity, visualization, etc.
        sharpe_filter : float
            A minimum Sharpe ratio to filter the results.

        Returns
        -------
        str or None
            A formatted string containing the results of the simulations, or None if there is nothing to print.
        """
        if 'ERROR' in results[0]:
            return results[0]

        summaries = {}
        compressions = ""
        periods = ""
        _results = []
        for n in range(0, len(results)):
            try:
                simulresults = results[n]
                if isinstance(simulresults, str):
                    print(simulresults)
                if not simulresults:
                    continue
                detail = simulresults.pop()
                _results.append({"simulresults": simulresults, 'detail': detail})
                compressions += f"{detail['feed'].compression}, "
                #if detail['feed'].compression != 1 and detail:
                period = detail['feed'].period.lower()[:3]+detail['feed'].period[-1]
                periods += f"{period}, "
            except (KeyError, IndexError):
                pass
        compressions = compressions.rstrip(", ")
        periods = periods.rstrip(", ")

        for n in range(0, len(_results)):
            try:
                simulresults = _results[n]['simulresults']
                detail = _results[n]['detail']
            except KeyError:
                print(f"Empty simulation results for feed({n})")
                continue

            df = pd.DataFrame.from_dict(simulresults)
            starting_cash: float = detail['starting_cash']

            if df.shape[0] <= 1:
                continue

            # Group dataframe by 'ref' to identify individual trades
            grouped_df = df.groupby('num')
            opening_trades = grouped_df.ngroups

            # Initiate empty lists to store roi_pct for profitable trades, loss trades, all trades and durations
            profitable_pnl = []
            loss_pnl = []
            all_pnl = []
            durations = []


            # Iterate over grouped_df and add roi_pct of closing trade to the lists and calculate durations
            for _, group in grouped_df:
                try:
                    closing_trade_pnl = group.iloc[-1]['roi']
                    duration = group.iloc[1]['timestamp'] - group.iloc[0]['timestamp']
                    durations.append(duration)
                    all_pnl.append(closing_trade_pnl)
                    if closing_trade_pnl > 0:
                        profitable_pnl.append(closing_trade_pnl)
                    elif closing_trade_pnl < 0:
                        loss_pnl.append(closing_trade_pnl)
                except IndexError:
                    logger.error("IndexError evaluating simul results, try removing pickle/* and try again")
                    logger.error("or seems last trade was not closed")
                    pass

            # Calculating metrics
            total_fees = round(df['fee'].sum(), 2)
            total_trades = grouped_df.ngroups
            profitable_trades = len(profitable_pnl)
            loss_trades = len(loss_pnl)
            win_rate = round((profitable_trades / total_trades) * 100, 4)
            average_return = round(np.mean(all_pnl), 4)
            median_return = round(np.median(all_pnl), 4)
            if len(loss_pnl) > 1:
                neg_std_dev = round(np.std(loss_pnl), 4)
            else:
                neg_std_dev = 0  # or some other value indicating an error or undefined result
            if len(profitable_pnl) > 1:
                pos_std_dev = round(np.std(profitable_pnl), 4)
            else:
                pos_std_dev = 0
            average_duration = round(np.mean(durations).total_seconds(), 4) # In seconds
            if len(all_pnl) > 1 and np.std(all_pnl) != 0:
                sharpe_ratio = round(average_return / np.std(all_pnl), 4)
            else:
                sharpe_ratio = 0  # np.nan  # or some other value indicating an error or undefined result

            if sharpe_ratio < sharpe_filter:
                return {}
            # Filter the DataFrame to include only rows where 'reason' is not null
            filtered_df = df[df['reason'].notnull()]
            # Calculate the sum of the 'pnlfee' column from the filtered DataFrame
            total_return = round(filtered_df['pnlfee'].sum(), 2)
            #total_return = detail['ending_assets'] - starting_cash
            roi = round(100 - (starting_cash - total_return) / starting_cash * 100, 2)
            # Starting and ending dates
            start_date = df['timestamp'].min()
            end_date = df['timestamp'].max()
            # Placeholder for Profit Factor, Recovery Factor
            profit_factor = "placeholder"
            recovery_factor = "placeholder"
            max_drawdown = (starting_cash - filtered_df['assets'].min()) / starting_cash * 100

            if max_drawdown < 0:
                max_drawdown = 0

            # Create summary dictionary
            summary = {
                'Strategy': detail['strategy'],
                'Symbol': detail['feed'].symbol,
                'Period': periods,
                'Compression': compressions,
                'Start Date': start_date,
                'End Date': end_date
            }
            if detail['params']['pairs'] is False:
                _ = detail['params'].pop('pairs')
            for remove in ['bot_id', 'uid', 'feeds', 'str_id']:
                _ = detail['params'].pop(remove)
            summary.update(detail['params'])
            summary.update({
                'params': detail['params'],
                'Total Trades': total_trades,
                'Profitable Trades': profitable_trades,
                'Loss Trades': loss_trades,
                'Win Rate (%)': win_rate,
                'Total Fees': total_fees,
                'Average Return %': average_return,
                'Total Return': total_return,
                'Total ROI %': roi,
                'Ending Cash': detail['ending_assets'],
                'Yield': detail['interest_earned'],
                'Median Return': median_return,
                'Negative Returns Standard Deviation': neg_std_dev,
                'Positive Returns Standard Deviation': pos_std_dev,
                'Average Duration (hours)': round(average_duration/60/60, 2),
                'Max Drawdown %': max_drawdown,
                'Profit Factor': profit_factor,
                'Recovery Factor': recovery_factor,
                'Sharpe Ratio': sharpe_ratio,
                'df': df
            })
            validate_keys = ['stop_loss', 'take_profit', 'trailing_stop', 'timeout', 'size_pct', 'size']
            for key in validate_keys:
                if key not in summary:
                    summary[key] = None
            summaries[n] = summary
        return summaries


    @staticmethod
    def round_floats_in_dict(d, decimal_places=2):
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, decimal_places)
        return d

    def calculate_final_summary(self, summaries: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:

        final_summary = {}
        n = len(summaries)
        # Static info
        static_keys = [
            'Strategy', 'Symbol', 'stop_loss', 'take_profit',
            'trailing_stop', 'timeout', 'size_pct', 'size',
            'leverage', 'params'
        ]
        final_summary.update(
            {key: summaries[0][key] for key in static_keys}
        )

        # Aggregated metrics
        aggregated_keys = [
            'Total Trades', 'Profitable Trades', 'Loss Trades',
            'Total Fees', 'Total Return', 'Total ROI %', 'Ending Cash',
            'Yield'
        ]
        final_summary.update(
            {key: sum(summaries[i][key] for i in summaries)
             for key in aggregated_keys}
        )

        # Averaged metrics
        averaged_keys = [
            'Win Rate (%)', 'Average Return %', 'Median Return',
            'Negative Returns Standard Deviation',
            'Positive Returns Standard Deviation',
            'Average Duration (hours)', 'Max Drawdown %', 'Sharpe Ratio'
        ]
        final_summary.update(
            {key: sum(summaries[i][key] for i in summaries) / n
             for key in averaged_keys}
        )

        dfs = [summaries[i]['df'] for i in summaries]
        final_summary.update({'df': dfs})

        # Date stuff
        final_summary['Start Date'] = summaries[0]['Start Date']
        final_summary['End Date'] = summaries[0]['End Date']
        final_summary['Compression'] = summaries[0]['Compression']
        final_summary['Period'] = summaries[0]['Period']
        final_summary = self.round_floats_in_dict(final_summary)

        return final_summary
