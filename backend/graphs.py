import numpy as np
import matplotlib.pyplot as plt

#  Comparison data (graphs 1–6)
methods = ['Proposed','B1','B2','B3','B4','B5']
accuracy = [92, 89, 88, 87, 86, 85]
precision= [91, 88, 87, 86, 85, 84]
recall   = [90, 87, 86, 85, 84, 83]
f1       = [91, 88, 87, 86, 85, 84]
latency  = [120,150,160,170,160,150]  # ms
convergence = [80,100,110,105,115,120]  # episodes

# Single-method data (graphs 7–12)
episodes = list(range(0,101,10))
reward = [100*(1-np.exp(-0.05*x)) for x in episodes]
loss   = [100*np.exp(-0.03*x) for x in episodes]
agents = list(range(1,11))
success_rate = [100 - (a-1)*2.5 for a in agents]   # approx
throughput    = [10/(1+0.1*(a-1)) for a in agents]
latency_agents= [100 + (a-1)*10 for a in agents]
utilization   = [100/(1+0.05*(a-1)) for a in agents]

# Common plot style
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except OSError:
    plt.style.use('seaborn-whitegrid')
plt.rcParams.update({'font.size': 12, 'figure.figsize': (6,4)})

def save_bar_chart(data, ylabel, title, fname):
    plt.figure()
    plt.bar(methods, data, color=['#4c72b0','#55a868','#c44e52','#8172b3','#ccb974','#64b5cd'])
    plt.title(title); plt.ylabel(ylabel); plt.xlabel('Method');
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(fname)

def save_line_chart(x, y, xlabel, ylabel, title, fname, legend=None):
    plt.figure()
    plt.plot(x, y, marker='o', color='#4c72b0')
    if legend: plt.legend([legend] if isinstance(legend,str) else legend)
    plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(fname)

# Generate all graphs
save_bar_chart(accuracy,    'Accuracy (%)',       'Accuracy Comparison',       'fig_accuracy.png')
save_bar_chart(precision,   'Precision (%)',      'Precision Comparison',      'fig_precision.png')
save_bar_chart(recall,      'Recall (%)',         'Recall Comparison',         'fig_recall.png')
save_bar_chart(f1,          'F1 Score (%)',       'F1 Score Comparison',       'fig_f1.png')
save_bar_chart(latency,     'Latency (ms)',       'Decision Latency Comparison','fig_latency.png')
save_bar_chart(convergence, 'Convergence (episodes)', 'Convergence Time Comparison','fig_convergence.png')

save_line_chart(episodes, reward, 'Episodes', 'Reward', 'Training Reward vs Episodes', 'fig_reward.png')
save_line_chart(episodes, loss,   'Episodes', 'Loss',   'Training Loss vs Episodes',   'fig_loss.png')
save_line_chart(agents, success_rate, 'No. of Agents', 'Success Rate (%)', 'Success vs Agents', 'fig_success.png')
save_line_chart(agents, throughput,    'No. of Agents', 'Throughput (tasks/sec)',  'Throughput vs Agents', 'fig_throughput.png')
save_line_chart(agents, latency_agents,'No. of Agents', 'Latency (ms)',          'Latency vs Agents',     'fig_latency_agents.png')
save_line_chart(agents, utilization,   'No. of Agents', 'Resource Utilization (%)','Utilization vs Agents','fig_utilization.png')
