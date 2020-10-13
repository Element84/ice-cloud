import matplotlib.pyplot as plt

def plot_h_li(ins, outs):
  plt.plot(ins['X'], ins['Z'], '.')
  plt.savefig('./plot_h_li.png')
  return True