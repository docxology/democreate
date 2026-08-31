```latex
\makeatletter
\@ifpackageloaded{geometry}
  {\geometry{margin=1.0in}}
  {\usepackage[margin=1.0in]{geometry}}
\@ifpackageloaded{hyperref}
  {\hypersetup{colorlinks=true, linkcolor=red, filecolor=magenta, urlcolor=red, citecolor=red}}
  {\usepackage{hyperref}\hypersetup{colorlinks=true, linkcolor=red, filecolor=magenta, urlcolor=red, citecolor=red}}
\makeatother

% Source code listings (used for CLI invocations and schema snippets)
\usepackage{listings}
\lstset{
  basicstyle=\ttfamily\small,
  breaklines=true,
  columns=fullflexible,
  frame=single,
  keepspaces=true,
  showstringspaces=false
}

% Units and quantities (frame geometry, sample rates, durations)
\usepackage{siunitx}

% Map the Unicode glyphs the prose uses to LaTeX equivalents so the default
% Latin-Modern font never silently drops them (xelatex/tectonic build).
\usepackage{amssymb}
\usepackage{newunicodechar}
\newunicodechar{✓}{\ensuremath{\checkmark}}
\newunicodechar{✗}{\ensuremath{\times}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{→}{\ensuremath{\rightarrow}}
\newunicodechar{−}{\ensuremath{-}}
\newunicodechar{×}{\ensuremath{\times}}
\newunicodechar{·}{\ensuremath{\cdot}}
\newunicodechar{…}{\ldots}

% Force newpage before References/Bibliography
\let\oldbibliography\bibliography
\renewcommand{\bibliography}[1]{\newpage\oldbibliography{#1}}
```
