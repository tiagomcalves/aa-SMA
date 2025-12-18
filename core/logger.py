# core/logger.py
from typing import Optional, Dict, Any
import csv
import json
from datetime import datetime
import os

class Logger:
    def __init__(self, verbose=False, problem_name="default"):
        self.verbose = verbose
        self.problem_name = problem_name
        self.learning_loggers: Dict[str, LearningLogger] = {}
        self.test_loggers: Dict[str, TestLogger] = {}

        # Cria diretórios para o problema específico
        if self.problem_name:
            os.makedirs(f"logs/{self.problem_name}/learning", exist_ok=True)

        print(f"Logger initialized for problem: {self.problem_name} {'--verbose' if verbose else ''}")

    def print(self, *args, **kwargs) -> None:
        print(*args, **kwargs)

    def vprint(self, *args, **kwargs) -> None:
        if self.verbose:
            print(*args, **kwargs)

    # ---------------------------------------------------
    # APRENDIZAGEM
    # ---------------------------------------------------
    def create_learning_logger(self, agent_name: str, timestamp, config: Dict[str, Any] = None) -> 'LearningLogger':
        """Cria um logger específico para aprendizagem do agente"""
        if agent_name not in self.learning_loggers:
            self.learning_loggers[agent_name] = LearningLogger(agent_name, timestamp, config or {}, self.problem_name)
            self.vprint(f"Created learning logger for agent: {agent_name}")
        return self.learning_loggers[agent_name]

    def get_learning_logger(self, agent_name: str) -> Optional['LearningLogger']:
        """Obtém logger de aprendizagem do agente"""
        return self.learning_loggers.get(agent_name)

    def log_learning_episode(self, agent_name: str, episode_data: Dict[str, Any]) -> None:
        """Regista um episódio de aprendizagem (método rápido)"""
        logger = self.get_learning_logger(agent_name)
        if logger:
            logger.log_episode(episode_data)
        else:
            # Cria logger automaticamente se não existir
            logger = self.create_learning_logger(agent_name)
            logger.log_episode(episode_data)

    # ---------------------------------------------------
    # GERAL
    # ---------------------------------------------------
    def close_all(self):
        """Fecha todos os loggers e salva dados"""
        self.vprint("💾 Saving all logs...")

        for logger in self.learning_loggers.values():
            logger.close()

        for logger in self.test_loggers.values():
            logger.close()

        self.vprint("All logs saved")

    @staticmethod
    def initialize(verbose=False, problem_name="default") -> None:  # CORRIGIDO: aceita 2 argumentos
        global _logger
        _logger = Logger(verbose, problem_name)


class LearningLogger:
    def __init__(self, agent_name: str, timestamp, config: Dict[str, Any], problem_name: str = "default"):
        self.agent_name = agent_name
        self.config = config
        self.problem_name = problem_name

        # Cria nome de ficheiro único com timestamp
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timestamp = timestamp

        # Diretório específico do problema
        log_dir = f"logs/{problem_name}/learning"
        os.makedirs(log_dir, exist_ok=True)

        self.csv_file = f"{log_dir}/{agent_name}_{timestamp}.csv"
        self.json_file = f"{log_dir}/{agent_name}_qtable_{timestamp}.json"

        # Inicializa ficheiros
        self._init_csv_file()

    def _init_csv_file(self):
        """Inicializa ficheiro CSV com cabeçalho"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'episode', 'total_reward', 'steps', 'success',
                'timestamp', 'epsilon', 'learning_rate', 'discount_factor',
                'q_table_size', 'successful_returns', 'food_collected', 'food_delivered',
                'avg_reward_last_10', 'success_rate_last_10'
            ])

    def log_episode(self, episode_data: Dict[str, Any]):
        """
        Regista um episódio de aprendizagem
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                episode_data.get('episode', 0),
                round(episode_data.get('total_reward', 0.0), 4),
                episode_data.get('steps', 0),
                1 if episode_data.get('success', False) else 0,
                timestamp,
                round(episode_data.get('epsilon', 0.0), 4),
                round(episode_data.get('learning_rate', 0.0), 4),
                round(episode_data.get('discount_factor', 0.0), 4),
                episode_data.get('q_table_size', 0),
                episode_data.get('successful_returns', 0),
                episode_data.get('food_collected', 0),
                episode_data.get('food_delivered', 0),
                round(episode_data.get('avg_reward_last_10', 0.0), 4),
                round(episode_data.get('success_rate_last_10', 0.0), 4)
            ])

    def save_q_table(self, q_table: Dict):
        """Salva a Q-table atual em formato JSON"""
        try:
            # Converte para formato serializável
            serializable_q = {}
            for key, value in q_table.items():
                if isinstance(key, tuple):
                    serializable_q[str(key)] = value
                else:
                    serializable_q[key] = value

            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_q, f, indent=2, default=str)

            return True
        except Exception as e:
            print(f"Error saving Q-table: {e}")
            return False

    def load_q_table(self) -> Optional[Dict]:
        """Carrega Q-table de ficheiro JSON"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Converte de volta para o formato original se necessário
            q_table = {}
            for key_str, value in data.items():
                # Tenta converter tuplas no formato "(a, b)"
                if key_str.startswith("('") and key_str.endswith("')"):
                    try:
                        # Converte string para tupla
                        key = eval(key_str)
                        q_table[key] = value
                    except:
                        q_table[key_str] = value
                else:
                    q_table[key_str] = value

            return q_table
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading Q-table: {e}")
            return None

    def close(self):
        """Fecha o logger (operação de limpeza se necessário)"""
        pass


class ReportLogger:
    def __init__(self, timestamp, problem: str = "default"):
        self.problem = problem
        self.timestamp = timestamp
        self.results = []

        # Diretório específico do problema
        log_dir = f"logs/{problem}/report"
        os.makedirs(log_dir, exist_ok=True)

        # Ficheiros de output
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.json_file = f"{log_dir}/{problem}_{timestamp}.json"
        self.csv_file = f"{log_dir}/{problem}_{timestamp}.csv"

        # Inicializa ficheiros
        self._init_csv_file()

    def _init_csv_file(self):
        """Inicializa ficheiro CSV com cabeçalho"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'name', 'steps', 'rewards', 'successes', 'success_rate',
                'avg_total_reward', 'avg_steps', 'avg_discounted_reward',
                'min_reward','max_reward',
                'total_successful','total_failed', 
                'food_collected', 'food_delivered'
            ])


    def retrieve_session_data(self, agent: 'Navigator2D', episodes):
        
        agent_session = {
            'name': agent.name,
            "episodes": episodes,
            'rewards': agent.session.rewards,
            'steps': agent.session.steps_per_ep,
            'successes': agent.session.successes,

            'food_collected': agent.ep.total_food_collected, 
            'food_delivered': agent.ep.total_food_delivered
        }

        print("GATHERED MAX EPISODES:", agent_session['episodes'])

        #log().print(agent_session)
        agent_session = {**agent_session, **self._calculate_statistics(agent_session)}
        
        self.results.append(agent_session)

    def save_report(self):
        """Salva relatório completo de teste"""
        if not self.results:
            return
        """
        # Calcula estatísticas
        stats = self._calculate_session_statistics()

        # Cria relatório completo
        report = {
            'timestamp': self.timestamp.now().isoformat(),
            'total_episodes': len(self.results),
            'episodes': self.results,
            'statistics': stats
        }

        # Salva JSON
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        """
        # Salva CSV resumido
        self._save_csv_summary()


    def _calculate_statistics(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula estatísticas dos resultados"""
        if not agent_data:
            return {}

        # Extrai dados
        successes = agent_data.get('successes', False)
        rewards = agent_data.get('rewards', 0)
        steps = agent_data.get('steps', 0)

        # Calcula estatísticas
        success_rate = successes.count(1) / len(successes) if len(successes) else 0

        # Calcula média
        avg_reward = sum(rewards) / len(rewards) if rewards else 0
        avg_steps = sum(steps) / len(steps) if steps else 0

        # Calcula recompensa descontada (γ=0.9)
        discounted_rewards = []
        for ep in range(agent_data.get('episodes', 1)):
            reward = agent_data.get('rewards', 0)[ep]
            steps_count = agent_data.get('steps', 1)[ep]
            discounted = reward * (0.9 ** (steps_count - 1))  # γ^(t-1)
            discounted_rewards.append(discounted)

        avg_discounted = sum(discounted_rewards) / len(discounted_rewards) if discounted_rewards else 0

        return {
            'success_rate': success_rate,
            'avg_total_reward': avg_reward,
            'avg_steps': avg_steps,
            'avg_discounted_reward': avg_discounted,
            'min_reward': min(rewards) if rewards else 0,
            'max_reward': max(rewards) if rewards else 0,
            'total_successful': successes.count(1),
            'total_failed': successes.count(0)
        }

    def _save_csv_summary(self):
        """Salva sumário em CSV"""
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            for line in self.results:
                writer.writerow([
                    line.get('name', 'name'),
                    line.get('steps', []),
                    line.get('rewards', []),
                    line.get('successes', []),
                    line.get('success_rate', '-1'),
                    line.get('avg_total_reward', '-1'),
                    line.get('avg_steps', '-1'),
                    line.get('avg_discounted_reward', '-1'),
                    line.get('min_reward', '-1'),
                    line.get('max_reward', '-1'),
                    line.get('total_successful', '-1'),
                    line.get('total_failed', '-1'),
                    line.get('food_collected', '-1'),
                    line.get('food_delivered', '-1'),
                ])


    def close(self):
        """Salva relatório ao fechar"""
        if self.results:
            self.save_report()


# Variável global e função de acesso
_logger: Optional[Logger] = None


def log() -> Logger:
    if _logger is None:
        raise RuntimeError("Logger not initialized — call Logger.initialize() from main")
    return _logger


# ---------------------------------------------------
# FUNÇÕES ÚTEIS PARA ANÁLISE
# ---------------------------------------------------
def load_learning_data(problem_name: str, agent_name: str = None):
    """Carrega dados de aprendizagem para análise"""
    import pandas as pd
    import os

    log_dir = f"logs/{problem_name}/learning"
    if not os.path.exists(log_dir):
        return None

    # Encontra todos os ficheiros CSV
    csv_files = []
    for file in os.listdir(log_dir):
        if file.endswith(".csv"):
            if agent_name is None or file.startswith(agent_name + "_"):
                csv_files.append(os.path.join(log_dir, file))

    if not csv_files:
        return None

    # Carrega e combina todos os dados
    all_data = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            df['agent'] = os.path.basename(file).split('_')[0]
            all_data.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)

    return None


def print_learning_summary(problem_name: str, agent_name: str):
    """Imprime sumário da aprendizagem"""
    data = load_learning_data(problem_name, agent_name)

    if data is None or data.empty:
        print(f"No learning data found for agent {agent_name} in problem {problem_name}")
        return

    print(f"\nRESUMO DE APRENDIZAGEM: {agent_name} ({problem_name})")
    print(f"Total de episódios: {len(data)}")
    print(f"Recompensa média: {data['total_reward'].mean():.2f}")
    print(f"Passos médios: {data['steps'].mean():.1f}")
    print(f"Taxa de sucesso: {data['success'].mean() * 100:.1f}%")

    if len(data) >= 10:
        last_10 = data.tail(10)
        print(f"\nÚLTIMOS 10 EPISÓDIOS:")
        print(f"Recompensa média: {last_10['total_reward'].mean():.2f}")
        print(f"Taxa de sucesso: {last_10['success'].mean() * 100:.1f}%")