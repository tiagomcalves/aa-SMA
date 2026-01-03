# Multi-Agent System Simulator

## Agents Phineas (Q-Learning) and Ferb (Fixed Policy)

Este projeto prático visa a construção de um simulador flexível em Python  
capaz de modelar e executar cenários típicos para sistemas multi-agente (SMA).  

O simulador deverá permitir a integração e avaliação de diferentes arquiteturas e  
estratégias de agentes autónomos em ambientes dinâmicos e cooperativos/competitivos.

---

## How does it run?

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

---

## UML Diagram

![draft](/draft.png "Rascunho")