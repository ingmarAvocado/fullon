"""
description
"""

import pandas as pd
from libs import log
from PIL import Image
import numpy as np
from tabulate import tabulate
from typing import List, Dict, Union, Any
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

    def echo_results(self,
                     bot: dict,
                     results: dict,
                     sharpe_filter: float = 0.0,
                     montecarlo: bool = False):
        """
         Processes the simulation results for output based on given filters.
        Args:
            results (list): A list of tuples containing bot configurations and their corresponding simulation results.
            sharpe_filter (float): Sharpe ratio filter for the results.
            short (bool): A flag for whether to shorten the output.
        Note:
            This function creates an instance of the 'simul' class to parse results and deletes it afterwards.
        """
        for str_id, result in results.items():
            self.echo_result(bot=bot, results=result, sharpe_filter=sharpe_filter, montecarlo=montecarlo)

    def echo_result(self, bot: dict,
                    results: list,
                    sharpe_filter: float = 0.0,
                    montecarlo: bool = False):
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
        _results = []
        for bot, result in results:
            # Parse simulation results according to bot's configuration
            summaries = self.parse(results=result, bot=bot, sharpe_filter=sharpe_filter)
            if summaries:
                summary = self.calculate_final_summary(summaries=summaries)
                if summary:
                    _results.append((result, summary))
        _results = sorted(_results, key=lambda x: x[1]['Total Return'], reverse=True)
        transformed_data = []
        if not _results:
            print("No trades, for any simulation apparently")
            return

        for result, summary in _results:
            self.verbose(dfs=summary['df'], bot=bot) if int(bot['verbose']) == 1 or int(bot['xls']) == 1 else None
            row = {**summary['params'], 'TP': summary['take_profit'], 'SL': summary['stop_loss'], 'TS': summary['trailing_stop'],
                   'TO': summary['timeout'], 'TTrades': summary['Total Trades'],
                   'Win rate %': summary['Win Rate (%)'], 'Fees': summary['Total Fees'],'Profit': summary['Total Return'],
                   'ROI': summary['Total ROI %'], 'AvgReturn': summary['Average Return %'],
                   'Duration': summary['Average Duration (hours)'],
                   'MedReturn': summary['Median Return'], 'NegStdDev': summary['Negative Returns Standard Deviation'],
                   'PosStdDev': summary['Positive Returns Standard Deviation'],
                   'Max Drawdown %': summary['Max Drawdown %'],
                   'SharpeRatio': summary['Sharpe Ratio']}
            transformed_data.append(row)

        # Creating the DataFrame
        res_df = pd.DataFrame(transformed_data)
        drop = ['size_pct', 'size_currency', 'leverage', 'size',
                'timeout', 'take_profit', 'stop_loss', 'trailing_stop']
        columns_to_drop = [col for col in drop if col in res_df.columns]
        res_df = res_df.drop(columns_to_drop, axis=1)
        red_df = res_df.sort_values(by='Profit', ascending=False)
        res_df = res_df.loc[:, res_df.iloc[0].notna()]
        symbol = _results[0][1]['Symbol']
        compression = _results[0][1]['Compression']
        period = _results[0][1]['Period']
        strategy = _results[0][1]['Strategy']
        start_date = _results[0][1]['Start Date']
        end_date = _results[0][1]['End Date']
        title = f"Strategy: {colored(strategy, 'green')} - "
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

    def _montecarlo(self, res_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform simulation results res_df into a new DataFrame with only Monte Carlo relevant results.
        Parameters:
            res_df (pd.DataFrame): The DataFrame containing the simulation results.
        Returns:
            pd.DataFrame: A DataFrame containing aggregated statistics for Monte Carlo simulations.
        """
        # Identifying the parameter columns (excluding the performance metrics columns)
        param_cols = [col for col in res_df.columns if col not in ['TTrades', 'Win rate %', 'Fees', 'Profit', 'ROI', 'AvgReturn', 'Duration', 'MedReturn', 'NegStdDev', 'PosStdDev', 'Max Drawdown %', 'SharpeRatio']]
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

    def verbose(self, dfs, bot):
        """description"""
        for feed, df in enumerate(dfs):
            if len(df) > 0:
                # Define desired column order, leave out columns that might not always be present
                column_order = ['ref', 'side', 'price', 'amount',
                                'cost', 'fee', 'roi', 'roi_pct',
                                'cash', 'assets', 'reason', 'timestamp']

                # Append new columns to the end of the list
                for col in df.columns:
                    if col not in column_order:
                        column_order.append(col)

                # Reorder the columns
                df = df[column_order]

                if int(bot['verbose']):
                    print(df.to_string())
                if int(bot['xls']):
                    filename= f"results_feed_{feed}.xls"
                    df.to_excel(filename, engine='openpyxl')
    def parse(self,
              results: List[Union[str, List[Dict[str, Any]]]],
              bot: Dict[str, int],
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

            for p in ['verbose', 'xls', 'visual']:
                if p not in bot.keys():
                    bot[p] = 0

            df = pd.DataFrame.from_dict(simulresults)

            if df.shape[0] <= 1:
                continue

            # Group dataframe by 'ref' to identify individual trades
            grouped_df = df.groupby('ref')

            # Initiate empty lists to store roi_pct for profitable trades, loss trades, all trades and durations
            profitable_roi_pct = []
            loss_roi_pct = []
            all_roi_pct = []
            durations = []
            all_assets = []
            starting_assets: float = 0


            # Iterate over grouped_df and add roi_pct of closing trade to the lists and calculate durations
            for num, group in grouped_df:
                try:
                    closing_trade_roi_pct = group.iloc[1]['roi_pct']
                    duration = group.iloc[1]['timestamp'] - group.iloc[0]['timestamp']
                    durations.append(duration)
                    all_roi_pct.append(closing_trade_roi_pct)
                    all_assets.extend(group['assets'].tolist())
                    if closing_trade_roi_pct > 0:
                        profitable_roi_pct.append(closing_trade_roi_pct)
                    elif closing_trade_roi_pct < 0:
                        loss_roi_pct.append(closing_trade_roi_pct)
                    if num == 1:
                        starting_assets = group.iloc[0]['assets']-group.iloc[0]['fee']
                except IndexError:
                    logger.error("IndexError evaluating simul results, try removing pickle/* and try again")
                    logger.error("or seems last trade was not closed")
                    pass

            # Calculating metrics
            total_fees = round(df['fee'].sum(),2)
            total_trades = len(all_roi_pct)
            profitable_trades = len(profitable_roi_pct)
            loss_trades = len(loss_roi_pct)
            win_rate = round((profitable_trades / total_trades) * 100, 4)
            average_return = round(np.mean(all_roi_pct), 4)
            median_return = round(np.median(all_roi_pct), 4)
            if len(loss_roi_pct) > 1:
                neg_std_dev = round(np.std(loss_roi_pct), 4)
            else:
                neg_std_dev = 0  # or some other value indicating an error or undefined result
            if len(profitable_roi_pct) > 1:
                pos_std_dev = round(np.std(profitable_roi_pct), 4)
            else:
                pos_std_dev = 0
            average_duration = round(np.mean(durations).total_seconds(), 4) # In seconds
            if len(all_roi_pct) > 1 and np.std(all_roi_pct) != 0:
                sharpe_ratio = round(average_return / np.std(all_roi_pct), 4)
            else:
                sharpe_ratio = 0 #np.nan  # or some other value indicating an error or undefined result

            if sharpe_ratio < sharpe_filter:
                return {}
            total_return = round(df['roi'].sum(), 2)
            roi = df.at[df.shape[0]-1, 'assets'] - 10000
            roi = round(100 - (10000 - roi) / 10000 * 100, 2)

            # Starting and ending dates
            start_date = df['timestamp'].min()
            end_date = df['timestamp'].max()

            # Placeholder for Profit Factor, Recovery Factor
            profit_factor = "placeholder"
            recovery_factor = "placeholder"

            all_assets_series = pd.Series(all_assets)

            # Calculate the max drawdown from the cumulative asset values
            if starting_assets != 0:
                max_drawdown = (starting_assets - all_assets_series.min()) / starting_assets * 100
            else:
                # Handle the case where starting_assets is 0 to avoid division by zero
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

        #so what happens is that results is a dict like {feed_number, simulation results}, some times i can have
        # two feeds with results (like when pairs trading)
        # but right now i am making two summaries, make it so that even if i have two feeds i return one (by doing matematics on each summary i guess)
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
            'Total Fees', 'Total Return', 'Total ROI %'
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
