import os
import streamlit.components.v1 as components

_RELEASE = True
if not _RELEASE:
    _component_func = components.declare_component(
        "draggable_barchart",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component("draggable_barchart", path=build_dir)


def draggable_barchart(name, key=None, labels=None):
    component_value = _component_func(name=name, key=key, labels=labels, default=[60, 60, 60, 60, 60])
    return component_value
