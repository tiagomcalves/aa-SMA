# core/logger.py
from typing import Optional, Dict, Any
import csv
import json
from datetime import datetime
import os


class Logger:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.learning_loggers: Dict[str, LearningLogger] = {}
        self.test_loggers: Dict[str, TestLogger] = {}

        # Cria diretórios necessários
        os.makedirs("logs/learning", exist_ok=True)
        os.makedirs("logs/test", exist_ok=True)

        print(f"Logger initialized {'--verbose' if verbose else ''}")

    def print(self, *args, **kwargs) -> None:
        print(*args, **kwargs)

    def vprint(self, *args, **kwargs) -> None:
        if self.verbose:
            print(*args, **kwargs)

    # ---------------------------------------------------
    # APRENDIZAGEM
    # ---------------------------------------------------
    def create_learning_logger(self, agent_name: str, config: Dict[str, Any] = None) -> 'LearningLogger':
        """Cria um logger específico para aprendizagem do agente"""
        if agent_name not in self.learning_loggers:
            self.learning_loggers[agent_name] = LearningLogger(agent_name, config or {})
            self.vprint(f"📝 Created learning logger for agent: {agent_name}")
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
    # TESTE
    # ---------------------------------------------------
    def create_test_logger(self, test_name: str) -> 'TestLogger':
        """Cria um logger específico para modo de teste"""
        if test_name not in self.test_loggers:
            self.test_loggers[test_name] = TestLogger(test_name)
            self.vprint(f"🧪 Created test logger: {test_name}")
        return self.test_loggers[test_name]

    def log_test_result(self, test_name: str, result_data: Dict[str, Any]) -> None:
        """Regista um resultado de teste"""
        logger = self.get_test_logger(test_name)
        if logger:
            logger.log_result(result_data)

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

        self.vprint("✅ All logs saved")

    @staticmethod
    def initialize(verbose=False) -> None:
        global _logger
        _logger = Logger(verbose)


class LearningLogger:
    """Logger para registar dados de aprendizagem por episódio"""

    def __init__(self, agent_name: str, config: Dict[str, Any]):
        self.agent_name = agent_name
        self.config = config

        # Cria nome de ficheiro único com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = f"logs/learning/{agent_name}_{timestamp}.csv"
        self.json_file = f"logs/learning/{agent_name}_qtable_{timestamp}.json"

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

        episode_data deve conter:
        - episode (int): número do episódio
        - total_reward (float): recompensa total
        - steps (int): número de passos
        - success (bool): se foi bem sucedido
        - epsilon (float): valor atual do epsilon
        - learning_rate (float): taxa de aprendizagem
        - discount_factor (float): fator de desconto
        - q_table_size (int): tamanho da Q-table
        - successful_returns (int): número de entregas bem sucedidas
        - food_collected (int): comida coletada
        - food_delivered (int): comida entregue
        - avg_reward_last_10 (float, opcional): média últimos 10 episódios
        - success_rate_last_10 (float, opcional): taxa sucesso últimos 10
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
            print(f"❌ Error saving Q-table: {e}")
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
            print(f"❌ Error loading Q-table: {e}")
            return None

    def close(self):
        """Fecha o logger (operação de limpeza se necessário)"""
        pass


class TestLogger:
    """Logger para registar resultados de teste"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.results = []

        # Ficheiros de output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.json_file = f"logs/test/{test_name}_{timestamp}.json"
        self.csv_file = f"logs/test/{test_name}_{timestamp}.csv"

    def log_result(self, result_data: Dict[str, Any]):
        """Regista um resultado de teste"""
        self.results.append(result_data)

    def save_report(self):
        """Salva relatório completo de teste"""
        if not self.results:
            return

        # Calcula estatísticas
        stats = self._calculate_statistics()

        # Cria relatório completo
        report = {
            'test_name': self.test_name,
            'timestamp': datetime.now().isoformat(),
            'total_episodes': len(self.results),
            'episodes': self.results,
            'statistics': stats
        }

        # Salva JSON
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        # Salva CSV resumido
        self._save_csv_summary(stats)

        return report

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calcula estatísticas dos resultados"""
        if not self.results:
            return {}

        # Extrai dados
        successes = [r for r in self.results if r.get('success', False)]
        rewards = [r.get('total_reward', 0) for r in self.results]
        steps = [r.get('steps', 0) for r in self.results]

        # Calcula estatísticas
        success_rate = len(successes) / len(self.results) if self.results else 0

        # Calcula média
        avg_reward = sum(rewards) / len(rewards) if rewards else 0
        avg_steps = sum(steps) / len(steps) if steps else 0

        # Calcula recompensa descontada (γ=0.9)
        discounted_rewards = []
        for r in self.results:
            reward = r.get('total_reward', 0)
            steps = r.get('steps', 1)
            discounted = reward * (0.9 ** (steps - 1))  # γ^(t-1)
            discounted_rewards.append(discounted)

        avg_discounted = sum(discounted_rewards) / len(discounted_rewards) if discounted_rewards else 0

        return {
            'success_rate': success_rate,
            'avg_total_reward': avg_reward,
            'avg_steps': avg_steps,
            'avg_discounted_reward': avg_discounted,
            'min_reward': min(rewards) if rewards else 0,
            'max_reward': max(rewards) if rewards else 0,
            'total_successful': len(successes),
            'total_failed': len(self.results) - len(successes)
        }

    def _save_csv_summary(self, stats: Dict[str, Any]):
        """Salva sumário em CSV"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Cabeçalho
            writer.writerow(['metric', 'value', 'description'])

            # Dados
            writer.writerow(['test_name', self.test_name, 'Nome do teste'])
            writer.writerow(['total_episodes', stats.get('total_episodes', 0), 'Total de episódios'])
            writer.writerow(['success_rate', f"{stats.get('success_rate', 0) * 100:.1f}%", 'Taxa de sucesso'])
            writer.writerow(['avg_total_reward', f"{stats.get('avg_total_reward', 0):.2f}", 'Recompensa média'])
            writer.writerow(['avg_steps', f"{stats.get('avg_steps', 0):.1f}", 'Passos médios'])
            writer.writerow(['avg_discounted_reward', f"{stats.get('avg_discounted_reward', 0):.2f}",
                             'Recompensa descontada média'])
            writer.writerow(['total_successful', stats.get('total_successful', 0), 'Episódios bem sucedidos'])
            writer.writerow(['total_failed', stats.get('total_failed', 0), 'Episódios falhados'])

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
def load_learning_data(agent_name: str = None):
    """Carrega dados de aprendizagem para análise"""
    import pandas as pd
    import os

    log_dir = "logs/learning"
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
            print(f"⚠️ Error reading {file}: {e}")

    if all_data:
        return pd.concat(all_data, ignore_index=True)

    return None


def print_learning_summary(agent_name: str):
    """Imprime sumário da aprendizagem"""
    data = load_learning_data(agent_name)

    if data is None or data.empty:
        print(f"📭 No learning data found for agent: {agent_name}")
        return

    print(f"\n📊 RESUMO DE APRENDIZAGEM: {agent_name}")
    print(f"📈 Total de episódios: {len(data)}")
    print(f"💰 Recompensa média: {data['total_reward'].mean():.2f}")
    print(f"👣 Passos médios: {data['steps'].mean():.1f}")
    print(f"🎯 Taxa de sucesso: {data['success'].mean() * 100:.1f}%")

    if len(data) >= 10:
        last_10 = data.tail(10)
        print(f"\n📈 ÚLTIMOS 10 EPISÓDIOS:")
        print(f"💰 Recompensa média: {last_10['total_reward'].mean():.2f}")
        print(f"🎯 Taxa de sucesso: {last_10['success'].mean() * 100:.1f}%")