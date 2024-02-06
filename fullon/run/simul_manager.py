#!/usr/bin/python3
"""
rpcdaemon_manager
"""
from __future__ import unicode_literals, print_function
import setproctitle
#from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import time
import numpy
from libs import log, simul
from run.bot_manager import BotManager
from typing import List, Dict
import decimal
from setproctitle import setproctitle
from concurrent.futures import ThreadPoolExecutor
import csv

logger = log.fullon_logger(__name__)


class SimulManager():

    @staticmethod
    def get_simul_comas(simuls, key, value):
        """ description """
        if not simuls:
            for child_val in value.split(','):
                try:
                    simuls.append({key: float(child_val)})
                except ValueError:
                    return [f'ERROR malformatted string 1 ({value}) \
                    por parameter {key}']
        else:
            simuls_tmp = []
            for sim in simuls:
                for child_val in value.split(','):
                    params = {}
                    params.update(sim)
                    try:
                        params.update({key: float(child_val)})
                    except ValueError:
                        return [f'ERROR malformatted string 2({value})\
                        for parameter {key}']
                    simuls_tmp.append(params)
            simuls = simuls_tmp
        return simuls

    @staticmethod
    def get_simul_dash_range(low: str, high: str) -> List:
        """
        Returns a list of values between low and high, with a step size that
        depends on the number of decimal places in the input
        """
        try:
            low = decimal.Decimal(low)
            high = decimal.Decimal(high)
            decimals = abs(low.as_tuple().exponent)
            if decimals == 0:
                low = int(low)
                high = int(high) + 1
                if low < 0 and high < 0:
                    low = abs(low)
                    high = abs(high)
                    val = range(low, high)
                    val = [-x for x in val]
                else:
                    val = range(low, high)
            else:
                if low < 0 and high < 0:
                    low = -low
                    high = -high
                    range_diff = high - low
                    num_points = int((range_diff * (10 ** decimals)))
                    val = [
                        round(
                            float(x),
                            decimals) for x in numpy.linspace(
                            float(low),
                            float(high),
                            num=num_points)]
                    val = [-x for x in val]
                else:
                    range_diff = high - low
                    num_points = int((range_diff * (10 ** decimals)))
                    val = [
                        round(
                            float(x),
                            decimals) for x in numpy.linspace(
                            float(low),
                            float(high),
                            num=num_points)]
        except decimal.InvalidOperation as error:
            raise ValueError("Invalid input, low and high must be valid numbers") from error
        return list(val)

    def get_simul_dash(self, simuls, key, value):
        """ description """
        try:
            low = value.split(':')[0]
            high = value.split(':')[1]
        except ValueError:
            return [f'ERROR malformatted string 2 ({value})\
            for parameter {key}']
        try:
            val = self.get_simul_dash_range(low, high)
        except ValueError as error:
            return [f'ERROR ({str(error)}) for parameter {key}']
        if len(val) == 0:
            return [f'ERROR malformatted string 3 (low, high order) ({value}) for parameter {key}']
        if not simuls:
            for child_val in val:
                try:
                    simuls.append({key: float(child_val)})
                except ValueError:
                    return [f'ERROR malformatted string  5 ({value}) for parameter {key}']
        else:
            simuls_tmp = []
            for sim in simuls:
                for child_val in val:
                    params = {}
                    params.update(sim)
                    try:
                        params.update({key: float(child_val)})
                    except ValueError:
                        return [f'ERROR malformatted string6 ({value}) for parameter {key}']
                    simuls_tmp.append(params)
            simuls = simuls_tmp
        return simuls


    @staticmethod
    def convert_value(value):
        try:
            return float(value)
        except (ValueError, TypeError) as error:
            if 'NoneType' in str(error) or 'false' in str(error) or 'convert string' in str(error):
                return None
            else:
                raise ValueError(f"The value for parameter must be a number " +
                                 f"but it is {value}. Could be that you're using '-' " +
                                 "instead of ':' for range?") from error

    def get_simul_param(self, simuls: list, key: str, value) -> list:
        """
        This function takes a list of simulations, a key and a value and
        updates the key-value pair of the simulations in the list.
        If the key is one of take_profit, stop_loss,  trailing_stop, timeout,
        the value is casted to float, otherwise it is left as is.
        :param simuls: list of dictionaries representing simulations
        :param key: key to update in the simulation dictionary
        :param value: value to update the key with
        :return: the updated list of simulation dictionaries
        """
        converted_value = self.convert_value(value)
        if not simuls:
            simuls.append({key: converted_value})
        else:
            for sim in simuls:
                sim.update({key: converted_value})
        return simuls

    def get_simul_list(self, simul_params: dict) -> list:
        """
         Constructs a list of simulation parameter sets based on a dictionary of simulation parameters.
        Args:
        simul_params (dict): Dictionary containing parameter-value pairs for simulations.

        Returns:
        list: A list of parameter sets for running simulations.

        Note:
        The method can return an 'ERROR' if it encounters one during list construction.
        """
        simuls = []
        for key, value in simul_params.items():
            if ',' in str(value):
                simuls = self.get_simul_comas(simuls=simuls, key=key, value=value)
                if simuls:
                    if 'ERROR' in simuls[0]:
                        return [simuls[0]]
            elif ':' in value:
                simuls = self.get_simul_dash(simuls=simuls, key=key, value=value)
                if simuls:
                    if 'ERROR' in simuls[0]:
                        return [simuls[0]]
            else:
                simuls = self.get_simul_param(simuls=simuls, key=key, value=value)
                if simuls:
                    if 'ERROR' in simuls[0]:
                        return [simuls[0]]
        return simuls

    def run_simul_and_update_progress(self, bot, event, feeds, params, progress_bar):
        """
        Executes a single simulation run and updates the associated progress bar by 1 unit.
        Args:
            bot: Bot configuration for the simulation.
            event: Specifies whether the simulation is event-based.
            feeds (dict): Additional feeds to be provided to the bot.
            params (dict): Parameters for the simulation.
            progress_bar (tqdm object): Progress bar for monitoring the simulations.
        Returns:
            result: The result of the simulation run.
        """
        result = self.run_simul(bot=bot, event=event, feeds=feeds, params=params)
        progress_bar.update(1)
        return result

    @staticmethod
    def load_from_file(filename: str) -> List[Dict]:
        """
        Loads simulation parameters from a specified file.
        Args:
            filename (str): The name of the file to load.
        Returns:
            List[Dict]: A list of dictionaries, each containing a set of simulation parameters.
        """
        filepath = f'simul_defs/{filename}'
        simulations = []

        def cast_to_number(value: str):
            """Try to cast a value to int or float, or return it unchanged."""
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value  # Return the value unchanged if it's not a number

        with open(filepath, newline='', encoding='utf-8-sig') as file:
            delimiter = ',' if ',' in file.read(1024) else '\t'  # Determine the delimiter
            file.seek(0)  # Reset file pointer to the beginning
            csvreader = csv.reader(file, delimiter=delimiter)
            header = next(csvreader)
            header = [item.strip() for item in header]  # Stripping spaces from header items
            for row in csvreader:
                simulation_dict = {key: cast_to_number(value.strip()) for key, value in zip(header, row)}
                # Renaming specific columns
                simulation_dict['take_profit'] = simulation_dict.pop('TP', None)
                simulation_dict['stop_loss'] = simulation_dict.pop('SL', None)
                simulation_dict['trailing_stop'] = simulation_dict.pop('TS', None)
                simulation_dict['timeout'] = simulation_dict.pop('TO', None)
                simulations.append(simulation_dict)
        return simulations

    def bot_simul(self, bot, event_based=False, feeds={}, params={}, sharpe_filter=0.0, filename=None, montecarlo=1):
        """
        Executes multiple simulation runs based on given parameters and updates a progress bar.
        Args:
            bot: Bot configuration for the simulation.
            event_based (bool, optional): Specifies if the simulations are event-based.
            feeds (dict, optional): Additional feeds for the bot.
            params (dict, optional): Parameters for the simulation.
            sharpe_filter (float, optional): Sharpe ratio filter.
        Returns:
            list: A list of tuples, each containing the bot configuration and the corresponding simulation result.
        """
        setproctitle("Fullon Simulator")
        if filename:
            sim_list = self.load_from_file(filename=filename)
        else:
            sim_list = self.get_simul_list(params)
        if not params:
            sim_list = [{}]
        progress_bar = tqdm(total=len(sim_list)*montecarlo, desc="Running Simulations")
        results = []
        start_time = time.perf_counter()
        with ThreadPoolExecutor() as executor:
            futures = {}
            for sim_param in sim_list:
                for _ in range(0, montecarlo):
                    future = executor.submit(
                        self.run_simul_and_update_progress,
                        bot, event_based, feeds, sim_param, progress_bar
                    )
                    futures[future] = sim_param
            for future in futures:
                result = future.result()
                results.append((bot, result))
        progress_bar.close()
        sim = simul.simul()
        sim.echo_results(bot=bot,
                         results=results,
                         sharpe_filter=sharpe_filter,
                         montecarlo=montecarlo > 1)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"\nRun time: {round(execution_time,5)}sec")

    def run_simul(self, bot: Dict, event=False, feeds={}, params=None) -> Dict:
        """
        This function runs a simulation based on the provided bot and simulation parameters. This function is designed
        to be used in a threading context.

        Args:
            bot (dict): A dictionary containing the bot's configuration and settings.
            event (bool, optional): A boolean indicating whether to run an event simulation or a regular simulation.
            feeds (dict, optional): Any additional feeds to be provided to the bot.
            params (optional): A dictionary containing additional parameters for the simulation.

        Returns:
            Dict: The results of the simulation, parsed according to the bot's configuration.
        """
        _params = {}
        if params:
            if 'ERROR' in params:
                logger.error(params)
                return []
            for key, value in params.items():
                if "." in str(value):
                    try:
                        _params[key] = float(value)
                    except ValueError:
                        _params[key] = value
                else:
                    try:
                        _params[key] = int(value)
                    except (ValueError, TypeError):
                        _params[key] = value
        periods = 365
        visual = None
        warm_up = False
        # Extract simulation parameters from bot dictionary
        if 'periods' in bot.keys():
            periods = int(bot['periods'])
        if 'visual' in bot.keys():
            visual = bot['visual']
        if 'warm_up' in bot.keys():
            warm_up = bot['warm_up']
        # Check that a bot_id is included in bot dictionary
        if 'bot_id' not in bot.keys():
            return ["Cant continue, no bot_id included in bot array"]
        # Launch simulation
        fullon_bot = BotManager()
        results = fullon_bot.launch_simul(bot_id=bot['bot_id'],
                                          periods=periods,
                                          visual=visual,
                                          warm_up=warm_up,
                                          event=event,
                                          feeds=feeds,
                                          test_params=_params)
        return results
