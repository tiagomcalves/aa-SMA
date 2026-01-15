# Multi-Agent System Simulator

## Agent Phineas (Q-Learning) and Ferb (Fixed Policy)

O presente projeto prático constitui um simulador flexível em Python capaz de modelar e executar cenários típicos para sistemas multi-agente (SMA), elaborado no âmbito da UC de Agentes Autónomos (1.º semestre do 3.º ano LEI, 2025/2026).

O simulador permite a integração e avaliação de diferentes arquiteturas e estratégias de agentes autónomos em ambientes dinâmicos e cooperativos/competitivos.

> **Nota:** O ficheiro README foi redigido em inglês para alinhar com os padrões da comunidade open-source e facilitar a análise técnica global. Como no enunciado não foi prevista uma língua específica para o presente ficheiro, optámos por elaborar desta forma.

---

### Elaborado por:
* **Aluno N.º 106090:** Tiago Miguel Camarão Alves
* **Aluno N.º 122123:** Rodrigo Miguel da Silva Delaunay

**UC Agentes Autónomos 2025/2026**
LEI - PL - ISCTE-IUL

---

## Scenario configuration

For each scenario, there is a separate subdirectory in `/problem` directory that corresponds to each scenario's name.
In every subdirectory, it must exist a configuration file named `config.json` that dictates environment and agents configurations.

For each agent, if the name contains "phineas", it turns into a Q-Learning agent.
Otherwise, it will turn into a "Ferb" agent, with a fixed, hardcoded behavior policy.

Here is an example of a configuration file for the **Lighthouse** problem (which should be located in `/problem/lighthouse`)

```json
{
  "environment": {
    "max_steps": 25,
    "sensor_handlers": ["surroundings", "directions"],
    "map": {
      "file": "map_example",
      "boundaries": [10, 10]
    }
  },

  "agents": {
    "Phineas_The_Worker": {
      "starting_position": [5, 5],
      "char": "P",
      "learning_rate": 0.1,
      "discount_factor": 0.9,
      "epsilon": 1.0,
      "epsilon_decay": 0.995,
      "kb": "1766876590.1993363"
    },
    "ferb": {
      "starting_position": [9, 8],
      "char": "B"
    }
  }
}
```

### By default, agents are ran in "learning/training mode"
### The only relevant parameters to the simulation <ins>outside of these files</ins> is the number of episodes and activating "agent testing mode", which is covered in the next section

---

## Launch Options

Usage:
`main.py <problem> [Optional parameters]`

Required parameter(s):
```txt
<problem> - The choosen simulated problem/scenario
          
Current available: 
- lighthouse
- foraging                         
```

Optional:
```
|   Options        | args         | description                                                                |
|------------------|--------------|----------------------------------------------------------------------------|
| -h | --help      | n/a          | show launch options                                                        |
| -a | --autostart | n/a          | automatically starts simulation                                            |
| -r | --renderer  | n/a          | renders board in separate process, mutually exclusive with --headless      |
| -l | --headless  | n/a          | run without board output or step delay, mutually exclusive with --renderer |
| -s | --step      | milliseconds | delay between steps, default=750                                           |
| -e | --episodes  | <int>        | number of episodes, default=5                                              |
| -t | --test      | n/a          | force reinforcement agents into testing mode                               |
| -v | --verbose   | n/a          | enable verbose output                                                      |
```

## Please note: -l is for --headless, not "learning mode".  The -h parameter is default for --help

### Example:

Launch a foraging simulation that **a**utostarts, with <ins>100</ins> **e**pisodes at 1500ms of **s**tep delay,  
on a separate renderer window (-r):

`main.py foraging -a -e 100 -s 1500 -r`


Here are the launch parameters used in the Report tests:

- Lighthouse learning/training: `lighthouse -e 100 --headless`
- Lighthouse testing: `lighthouse -e 100 --headless -t`
- Foraging learning/training: `foraging -e 100 --headless`
- Foraging testing: `foraging -e 100 --headless -t`

(pretty repetitive)

After a simulation, different graph prompts will show up after the simulation, waiting for your decision **y** or **n**:
```
Generating graphs of session 1768431755.4790132 with 100 episodes:
Show learning graph of simulation? (y/n):
...
Generating heatmap of session 1768431755.4790132
Show heatmap of simulation? (y/n): 
...
Generating graphs of session 1768431755.4790132 with 100 episode(s):
Show session graph of simulation? (y/n): 
```

Note: the learning graph only prompts in learning mode.

 
### Ok, I ran a learning/training simulation, how can I use the results in test?

Let's say that you used `main.py lighthouse -e 100 -l`, this is the last output in the terminal:
```
============================================================
EPISODIO CONCLUÍDO 
Total de steps: 16
agentes ativos: 0
SIMULAÇÃO CONCLUÍDA
Generating graphs of session 1768431755.4790132 with 100 episodes:
Show learning graph of simulation? (y/n): 
```

Copy the timestamp `1768431755.4790132` and place it in the corresponding problem configuration file, the corresponding agent.  
In this case it would be the lighthouse problem:

```
    ...
    
  "agents": {
    "Phineas_The_Worker": {
      "starting_position": [5, 5],
      "char": "P",
      "learning_rate": 0.1,
      "discount_factor": 0.9,
      "epsilon": 1.0,
      "epsilon_decay": 0.995,
      "kb": "1768431755.4790132"    <<-- change the timestamp in this parameter 
    },
    
    ...
```


## UML Diagram

![draft](/draft.png "Rascunho")

### Note

There is also a tool to review past session graphs: `util.py`
```
usage: util.py problem timestamp
optional: '-q' or '--qlearning': "show only qlearning graphs"
```
