# JRPG Engine Suite

A comprehensive JRPG game development suite built in Python, designed for AI-assisted development.

## Features

- **Modern Rendering**: Pygame + ModernGL for GPU-accelerated graphics
- **Dynamic Lighting**: Point lights, day/night cycle, shadows
- **Particle System**: GPU-accelerated particles with presets
- **Post-Processing**: Bloom, vignette, color grading, screen transitions
- **ECS Architecture**: Data-only components, logic-only systems
- **Turn-Based Battle**: Complete JRPG combat system
- **Dialog System**: Typewriter effect, portraits, branching choices
- **Quest System**: Objectives, tracking, rewards
- **Save/Load**: Multiple slots, game flags, state persistence
- **Visual Editor**: ImGui-based dockable panels

## Requirements

```
Python 3.10+
pygame>=2.0
moderngl>=5.0
imgui-bundle>=1.0
numpy>=1.20
```

## Installation

```bash
pip install pygame moderngl imgui-bundle numpy
```

## Quick Start

```bash
# Verify codebase integrity
python verify_codebase.py

# Run demos
python demos/phase1_demo.py  # Core ECS
python demos/phase2_demo.py  # GPU Graphics
python demos/phase3_demo.py  # Editor
python demos/phase4_demo.py  # Full JRPG
```

## Architecture

```
engine/          # Core engine (reusable)
├── core/        # ECS, events, game loop
├── graphics/    # GPU rendering pipeline
└── input/       # Action-based input

framework/       # JRPG-specific systems
├── components/  # Data-only components
├── systems/     # Logic processors
├── world/       # Maps, entities
├── dialog/      # Conversation system
├── battle/      # Turn-based combat
├── progression/ # Skills, quests
├── inventory/   # Items, equipment
└── save/        # Persistence

editor/          # Development tools
├── panels/      # Dockable UI panels
└── imgui_backend.py
```

## Design Principles

1. **AI-Friendly**: Modular, pattern-consistent, well-typed
2. **Data-Driven**: Components hold data, systems hold logic
3. **Typed Events**: Enums prevent magic strings
4. **Action-Based Input**: Abstract input for rebinding
5. **Hot Reload Ready**: Asset watcher architecture

## Development Phases

- [x] Phase 1: Core Engine (ECS, events, input)
- [x] Phase 2: GPU Rendering (lighting, particles, post-fx)
- [x] Phase 3: Editor Foundation (ImGui panels)
- [x] Phase 4: JRPG Framework (battle, dialog, quests)
- [ ] Phase 5: Polish (audio, localization, transitions)

## License

MIT
