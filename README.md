# The Last Ingredient

<p align="center">
  <em>"One Chance to Begin Again."</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Engine-Arcade%203.x-orange" alt="Arcade Engine">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-brightgreen" alt="Cross Platform">
  <img src="https://img.shields.io/badge/Course-ISE%20Group%2019-purple" alt="ISE Group 19">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License">
</p>

---

## 📖 Overview

**The Last Ingredient** is an immersive 2D narrative cooking adventure built with Python and the [Arcade](https://api.arcade.academy/) library.

After a devastating restaurant food poisoning incident caused by an unverified sample, a dedicated chef loses everything: his career, his savings, and his family home. Desperate and wandering on a cold, rain-swept night, he slips into his foreclosed home to cook one final comforting bowl of egg noodle soup. At midnight (00:00), three mystical tarot cards—**The Beast**, **The Crown**, and **The Gear**—transport his consciousness across prehistory, a medieval royal palace, and a high-tech quantum laboratory.

Along this journey through time, he uncovers a shocking temporal paradox: **the tragedies across all four eras originated from his own desperate attempts to travel back in time and "save" everyone.**

---

## 🎮 Key Features

* **🕰️ 4 Interconnected Historical & Futuristic Eras**:
  * **Modern Era**: High-end restaurant kitchen, forensic toxicological interrogation, court liquidation, and stealthy backyard break-in on a stormy night.
  * **Prehistoric Era**: Primeval caves, mammoth & dinosaur open-flame hearth roasting, and primal tribal feast ceremonies.
  * **Royal Court Era**: Medieval palace cuisine, ingredient prep, royal banquet plating, and court intrigue.
  * **Future Quantum Lab**: High-tech synthesis island, chemical crystal spectroscopy, and temporal jump telemetry.

* **🍳 Tactile, Cooking Mama-Style Interactive Minigames**:
  * **First-Person Steak Carving**: Dynamic dragging knife physics with sizzling steam and audio feedback.
  * **Forensic Crystal Lattice Focus**: Interactive microscope focus slider to detect Compound CX-47 neurotoxin.
  * **Realistic 4-Pin Tumbler Lockpicking**: Manual blade insertion, pin height alignment, audio sweet spot cues, and cylinder binding.
  * **Step-by-Step Noodle Soup Assembly**: Water filling, stove ignition, noodle boiling, sunny-side-up egg skillet frying, eggshell retrieval, and garnish assembly.
  * **Rapid-Tap Gate Vaulting**: Momentum gauge build-up and sprint-tap gate scaling.

* **🎭 Dual Branching Endings**:
  * **Bad Ending (`A Fate of My Own Making`)**: Driven by obsession to control destiny, the protagonist launches the time-warp apparatus, re-igniting the cycle of tragedy anew.
  * **True / Happy Ending (`One More Tomorrow`)**: He accepts imperfection and aborts the jump. The poison causal chain dissolves. He awakens in a warm morning home beside his wife, who wears the heirloom sun-and-vine ring passed down across centuries: *"Eat first. We'll face tomorrow when it comes."*

* **🎨 Audiovisual Polish & Dynamic Camera**:
  * Native fullscreen startup with smooth toggle to windowed mode (`F11`).
  * Seamless support for both **16:9** and **16:10** widescreen aspect ratios.
  * Pre-computed stable word-wrapping with typewriter effect and zero text jitter.
  * Parallax street scrolling, animated rain ripples, lightning flashes, camera shockwaves, and dolly zooms.

---

## 🕹️ Controls & Keybindings

| Action | Primary Controls | Alternative Controls |
| :--- | :--- | :--- |
| **Character Movement** | `W` `A` `S` `D` | Arrow Keys (`↑` `←` `↓` `→`) |
| **Sprint / Fast Walk** | Hold `Shift` + Move | — |
| **Interact / Inspect** | `E` | Left Mouse Click |
| **Advance Dialogue** | `Space` / `Enter` / `E` | Left Mouse Click |
| **Toggle Fullscreen** | `F11` | — |
| **Pause Menu / Settings** | `Escape` | Pause Button (Top-Right) |

---

## 🚀 Installation & Quick Start

### Prerequisites
* Python 3.10, 3.11, 3.12, or 3.13.

### Running the Game

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the game**:
   ```bash
   python main.py
   ```

---

## 📁 Project Architecture

```text
TheLastIngredient/
├── main.py                     # Main game entry point & window manager
├── requirements.txt            # Python dependencies (arcade>=3.0.0, pillow, numpy)
├── README.md                   # Project documentation & gameplay guide
├── .gitignore                  # Optimized Git ignore specifications
│
├── core/                       # Shared engine subsystems
│   ├── constants.py            # Global dimensions, audio tokens, dynamic resolvers
│   ├── base_view.py            # Base view class, Win32 composite hooks, camera projection
│   ├── player.py               # Top-down player character controller & collision
│   ├── dialogue.py             # Sub-pixel crisp dialogue & typography engine
│   ├── audio.py                # Audio manager, SFX and ambient sound loopers
│   ├── achievements.py         # Persistent unlockable achievement tracker
│   └── particles.py            # Steam, spark, ripple, and dust particle emitters
│
├── scenes/                     # Story scenes and interactive views (58 modules)
│   ├── menu_view.py            # S00 Main Menu & Prologue Hub
│   ├── modern_view.py          # S01 Modern Michelin Kitchen (Steak Carving)
│   ├── scene_2_view.py         # S02 The Unverified Sample (Sealing & Warning)
│   ├── scene_3_view.py         # S03 The Incident (5-Panel Comic Montage)
│   ├── scene_4_view.py         # S04 Legal Liquidation & Courtroom
│   ├── scene_5_view.py         # S05 Stormy Night (Street & Mansion Navigation)
│   ├── scene_6_home_kitchen_view.py # S06 Foreclosed Home (Living Room & Kitchen)
│   ├── scene_7_kitchen_view.py # S07 Midnight Egg Noodle Cooking
│   ├── scene_8_view.py         # S08 The Clock Strikes Midnight (Card Revelation)
│   ├── prehistoric_view.py     # Act I: Primeval Era (Gathering & Exploration)
│   ├── prehistoric_bbq_view.py # Act I: Open-Flame Hearth Roasting
│   ├── royal_view.py           # Act II: 1910 Royal Court Banquet Preparation
│   ├── future_integrated_view.py # Act III: Integrated Future Laboratory
│   ├── bad_ending_view.py      # B01-B07 Bad Ending Sequence
│   └── happy_ending_view.py    # H01-H11 True / Happy Ending Sequence
│
└── assets/                     # Clean, production-ready audiovisual assets
    ├── characters/             # Character spritesheets (Modern, Chef, Savage, etc.)
    ├── sounds/                 # Sound effects & ambient loops
    ├── tarot/                  # Tarot card illustrations
    └── ...                     # Era-specific backgrounds & minigame assets
```
