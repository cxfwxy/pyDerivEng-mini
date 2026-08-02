"""
事件总线
--------------------------------
发布/订阅：
  - subscribe(EventType, handler)：注册某类事件的处理函数
  - publish(event)：发布事件
  - run()：循环处理队列直至清空
"""
from collections import defaultdict, deque
from typing import Callable, Dict, List, Type
from .events import Event


class EventBus:
    def __init__(self):
        self._handlers: Dict[type, List[Callable[[Event], None]]] = defaultdict(list) # 事件类型 -> 处理函数列表
        self._queue = deque() # 事件队列
        self._history: List[Event] = [] # 事件历史记录（按顺序记录所有已处理的事件）

    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> None:
        """注册某类事件的处理函数"""
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        """发布事件"""
        self._queue.append(event)

    def run(self) -> None:
        """循环处理队列直至清空"""
        while self._queue:
            event = self._queue.popleft()
            self._history.append(event)
            for handler in self._handlers.get(type(event), []):
                handler(event)

    @property
    def history(self) -> List[Event]:
        """返回已处理的事件历史记录"""
        return list(self._history)

    def print_history(self) -> None:
        """打印已处理的事件历史记录"""
        for e in self._history:
            print(f"[{e.event_type:16s}] {e}")
