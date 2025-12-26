import pytest
from enum import Enum, auto
from engine.core.events import EventBus, Event

class MockEvent(Enum):
    TEST_EVENT = auto()
    OTHER_EVENT = auto()

def test_event_bus_subscribe_publish(event_bus):
    received = []
    def handler(event):
        received.append(event)
    
    event_bus.subscribe(MockEvent.TEST_EVENT, handler)
    event_bus.publish(MockEvent.TEST_EVENT, data="test")
    
    assert len(received) == 1
    assert received[0].type == MockEvent.TEST_EVENT
    assert received[0].data["data"] == "test"

def test_event_bus_unsubscribe(event_bus):
    received = []
    def handler(event):
        received.append(event)
    
    event_bus.subscribe(MockEvent.TEST_EVENT, handler)
    event_bus.unsubscribe(MockEvent.TEST_EVENT, handler)
    event_bus.publish(MockEvent.TEST_EVENT)
    
    assert len(received) == 0

def test_event_priority(event_bus):
    order = []
    
    event_bus.subscribe(MockEvent.TEST_EVENT, lambda e: order.append("low"), priority=1, weak=False)
    event_bus.subscribe(MockEvent.TEST_EVENT, lambda e: order.append("high"), priority=10, weak=False)
    event_bus.subscribe(MockEvent.TEST_EVENT, lambda e: order.append("normal"), priority=5, weak=False)
    
    event_bus.publish(MockEvent.TEST_EVENT)
    
    assert order == ["high", "normal", "low"]

def test_event_consumption(event_bus):
    received = []
    
    def consumer(event):
        received.append("consumer")
        event.consume()
        
    def later_handler(event):
        received.append("later")
        
    event_bus.subscribe(MockEvent.TEST_EVENT, consumer, priority=10)
    event_bus.subscribe(MockEvent.TEST_EVENT, later_handler, priority=5)
    
    event_bus.publish(MockEvent.TEST_EVENT)
    
    assert received == ["consumer"]
