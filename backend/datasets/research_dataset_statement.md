## Dataset and Graph Source Statement

This project uses a simulation-generated dataset, not an external public dataset.

### Where values come from

- Comparative metrics and graph values are defined in:
  - `backend/Research_Comparison_Graphs.ipynb`
  - `backend/graphs.py`
- Graph image files are generated from those values and saved as:
  - `backend/fig_accuracy.png`, `backend/fig_precision.png`, `backend/fig_recall.png`, `backend/fig_f1.png`
  - `backend/fig_latency.png`, `backend/fig_convergence.png`
  - `backend/fig_reward.png`, `backend/fig_loss.png`
  - `backend/fig_success.png`, `backend/fig_throughput.png`, `backend/fig_latency_agents.png`, `backend/fig_utilization.png`

### Experimental setup used in the notebook

- Environment: `6x6` grid road network
- Agents: `4` (default setting)
- Road spacing: `100` units
- Training horizon: `200` episodes
- Averaging: `5` runs (as documented in notebook markdown)

### Important transparency note

Current plotted values are manually specified arrays and formula-generated sequences in the notebook/script. They are not imported from Kaggle/UCI/OpenML files.

To avoid academic issues, describe these results as **simulation-derived** and include the CSV files in this folder as the dataset behind the graphs.
