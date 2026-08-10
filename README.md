# Mini Equity OTC Derivatives Pricing Engine (Demo)

一个用于面试展示的**权益场外衍生品定价/风险/簿记系统**精简实现。

实现功能：
- 合约：欧式期权、标准雪球
- 定价方法：BS解析解、MC方法（CPU）、MC方法（GPU）、PDE（CN方法）
- 驱动方式：事件驱动（行情变化）
- 希腊值计算：Delta、Gamma、Vega、Theta、Rho
- 情景分析：支持标的价格变动、波动率变动、无风险收益率变动
- 其他：现金流计算、合约生命周期管理、交易簿记等功能

不足：
- 计算时波动率为定值，未考虑波动率变化


## 快速开始

```bash
pip install -r requirements.txt   # 安装依赖
python run_demo.py                # 运行demo
pytest -v                         # 运行单元测试
```

## 项目结构

```
equity-otc-pricer/
├── engine/                   # 事件驱动
│   ├── events.py             #   事件定义
│   ├── event_bus.py          #   事件总线
│   └── market_data.py        #   行情快照
│
├── contracts/                # 合约层
│   ├── base.py               #   合约抽象基类
│   ├── european_option.py    #   欧式期权
│   └── snowball.py           #   经典雪球
│
├── pricers/                  # 定价算法
│   ├── base.py               #   PricerBase / PricingResult
│   ├── bs_pricer.py          #   BS解析解（欧式期权）
│   ├── pde_pricer.py         #   TBD PDE CN（欧式期权）
│   ├── mc_pricer_cpu.py      #   MC CPU 实现（欧式 & 雪球）
│   └── mc_pricer_cuda.py     #   TBD MC GPU 实现（欧式 & 雪球）
│
├── risk/                     # 风险场景
│   ├── greeks.py             #   计算希腊值
│   └── scenario.py           #   场景分析
│
├── cashflow/                 # 现金流
│   └── cashflow_engine.py    #   TBD 计算现金流
│
├── lifecycle/                # 合约生命周期
│   └── barrier_monitor.py    #   检测雪球敲入/敲出/到期
│
├── portfolio/                # 持仓部分
│   ├── portfolio.py          #   持仓管理
│   └── position.py           #   持仓定义
│
├── tests/                    # pytest测试
├── run_demo.ipynb            # TBD
├── requirements.txt          # 依赖库
└── pytest.ini
```