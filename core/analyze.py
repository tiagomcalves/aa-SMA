# analyze.py (simples)
from core.logger import load_learning_data, print_learning_summary
import pandas as pd
import matplotlib.pyplot as plt


def plot_learning_curve(agent_name: str):
    """Gráfico simples da curva de aprendizagem"""
    data = load_learning_data(agent_name)

    if data is None or data.empty:
        print(f"No data for {agent_name}")
        return

    plt.figure(figsize=(12, 4))

    # Recompensa
    plt.subplot(1, 3, 1)
    plt.plot(data['episode'], data['total_reward'], alpha=0.3, label='Por episódio')

    if len(data) > 10:
        data['reward_ma'] = data['total_reward'].rolling(window=10).mean()
        plt.plot(data['episode'], data['reward_ma'], 'r-', linewidth=2, label='Média móvel (10)')

    plt.xlabel('Episódio')
    plt.ylabel('Recompensa')
    plt.title(f'{agent_name} - Curva de Aprendizagem')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Taxa de sucesso
    plt.subplot(1, 3, 2)
    if len(data) > 10:
        data['success_ma'] = data['success'].rolling(window=10).mean() * 100
        plt.plot(data['episode'], data['success_ma'])
        plt.ylim([0, 100])

    plt.xlabel('Episódio')
    plt.ylabel('Taxa Sucesso (%)')
    plt.title('Taxa de Sucesso')
    plt.grid(True, alpha=0.3)

    # Epsilon
    plt.subplot(1, 3, 3)
    plt.plot(data['episode'], data['epsilon'])
    plt.xlabel('Episódio')
    plt.ylabel('ε')
    plt.title('Exploração vs Exploração')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"logs/learning/{agent_name}_curve.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    # Exemplo de uso
    print_learning_summary("Phineas_The_Worker")
    plot_learning_curve("Phineas_The_Worker")