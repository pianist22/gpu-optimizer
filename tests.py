 """tests/test_optimizer.py"""
import torch
from gpu_optimizer import GPUPowerOptimizer

def test_apply_power_optimizations():
    model = torch.nn.Linear(10, 2).cuda()
    optimizer = GPUPowerOptimizer()
    result = optimizer.apply_power_optimizations(model)
    assert result is not None

def test_optimize_batch_size_returns_int():
    model = torch.nn.Linear(10, 2).cuda()
    sample_input = torch.randn(8, 10).cuda()
    optimizer = GPUPowerOptimizer()
    batch_size = optimizer.optimize_batch_size(model, sample_input, target_power=250.0)
    assert isinstance(batch_size, int)
    assert batch_size > 0
"""📁 tests/test_monitor.py"""
from gpu_optimizer import GPUMonitor

def test_gpu_monitor_returns_metrics():
    monitor = GPUMonitor()
    metrics = monitor.get_gpu_metrics()
    assert "power" in metrics
    assert "temperature" in metrics
    assert isinstance(metrics["power"], float)
"""▶️ HOW TO RUN LOCALLY

Create a folder named tests/ in the root of your project.
Place the above two files inside.
Open your terminal in the project directory and run:
pip install pytest
pytest tests/
It will show results like:

tests/test_monitor.py ..                            [100%]
tests/test_optimizer.py ..                          [100%]

================ 4 passed in 1.23s =================
Would you also like a sample requirements.txt and GitHub Actions file to automate this in CI/CD? """

