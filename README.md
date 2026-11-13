# games

Terminal games you install and run with two commands.

    load tetris     # downloads the game
    run             # starts the most recently loaded game

## Install (once)

Linux, macOS, Termux:

    curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/games/main/install.sh | bash

or with git:

    git clone https://github.com/YOUR_GITHUB_USERNAME/games && bash games/install.sh

Windows (PowerShell):

    irm https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/games/main/install.ps1 | iex

Then open a new terminal and play:

    load tetris
    run

## Controls

Left/Right move, Up rotate, Down soft drop, PgDn / Enter / Insert hard drop,
Home pause, End restart, Esc or Ctrl+C quit.
