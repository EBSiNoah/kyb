(() => {
  'use strict';
  const main = document.querySelector('main');
  if (!main) return;

  const is3d = Boolean(document.getElementById('scene'));
  const panelFor = selector => document.querySelector(selector)?.closest('.panel') || null;
  const unique = items => [...new Set(items.filter(Boolean))];
  const sidebar = document.createElement('aside');
  sidebar.className = 'workspace-sidebar';
  sidebar.setAttribute('aria-label', is3d ? '편집 및 미로 생성 메뉴' : '편집 및 환경 설정 메뉴');
  const rightbar = document.createElement('aside');
  rightbar.className = 'workspace-rightbar';
  rightbar.setAttribute('aria-label', is3d ? '이동 및 경로 탐색 메뉴' : '경로 탐색 및 직접 이동 메뉴');
  const stage = document.createElement('div');
  stage.className = 'workspace-stage';
  const workspace = document.createElement('div');
  workspace.className = is3d ? 'workspace-layout workspace-3d' : 'workspace-layout workspace-2d';

  const menuPanels = is3d
    ? unique([
        panelFor('[data-mode]'),
        panelFor('#start-x'),
        panelFor('#maze-kruskal'),
        panelFor('#game-start'),
        panelFor('#run')
      ])
    : unique([
        panelFor('[data-mode]'),
        panelFor('#start-x'),
        panelFor('#density'),
        panelFor('#random'),
        panelFor('#game-start')
      ]);
  const rightPanels = is3d
    ? unique([panelFor('#game-start'), panelFor('#run')])
    : unique([panelFor('#game-start')]);
  const leftPanels = menuPanels.filter(panel => !rightPanels.includes(panel));
  const scenePanel = panelFor(is3d ? '#scene' : '#grid');
  const statsPanel = document.querySelector('#expanded')?.closest('section.stats') || null;
  const featurePanel = main.querySelector('[aria-label="3D 실험실"]');
  const excluded = new Set([...menuPanels, scenePanel, statsPanel, featurePanel].filter(Boolean));
  const extras = [...main.querySelectorAll('.panel')].filter(panel => !excluded.has(panel));
  if (!menuPanels.length) return;

  const layoutStyles = document.createElement('style');
  layoutStyles.textContent = `
    .workspace-layout.workspace-2d{grid-template-columns:minmax(230px,300px) minmax(0,1fr) minmax(250px,300px);gap:12px}
    .workspace-layout.workspace-2d .workspace-rightbar{min-width:0}
    .workspace-layout.workspace-2d .workspace-rightbar .workspace-panel{margin:0 0 10px}
    .workspace-layout.workspace-2d .workspace-search-controls{display:grid;grid-template-columns:1fr;gap:8px}
    .workspace-layout.workspace-2d .workspace-search-controls label{min-width:0}
    .workspace-layout.workspace-2d .workspace-search-controls button{width:100%}
    .workspace-layout.workspace-2d .move-pad{width:min(100%,210px);grid-template-columns:repeat(3,minmax(48px,1fr));gap:6px}
    .workspace-layout.workspace-2d .move-pad button{min-width:0;padding:8px 4px;font-size:20px;font-weight:700}
    .workspace-layout.workspace-2d .move-pad [data-move2d="-1,0"],
    .workspace-layout.workspace-2d .move-pad [data-move2d="1,0"]{background:#fef2f2;border-color:#fecaca;color:#b91c1c}
    .workspace-layout.workspace-2d .move-pad [data-move2d="-1,0"]:hover:not(:disabled),
    .workspace-layout.workspace-2d .move-pad [data-move2d="1,0"]:hover:not(:disabled){background:#fee2e2}
    .workspace-layout.workspace-2d .move-pad [data-move2d="0,-1"],
    .workspace-layout.workspace-2d .move-pad [data-move2d="0,1"]{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8}
    .workspace-layout.workspace-2d .move-pad [data-move2d="0,-1"]:hover:not(:disabled),
    .workspace-layout.workspace-2d .move-pad [data-move2d="0,1"]:hover:not(:disabled){background:#dbeafe}
    .workspace-layout.workspace-2d .move-pad [data-move2d="-1,-1"],
    .workspace-layout.workspace-2d .move-pad [data-move2d="1,-1"],
    .workspace-layout.workspace-2d .move-pad [data-move2d="-1,1"],
    .workspace-layout.workspace-2d .move-pad [data-move2d="1,1"]{background:#f5f3ff;border-color:#ddd6fe;color:#6d28d9}
    .workspace-layout.workspace-2d .move-pad [data-move2d="-1,-1"]:hover:not(:disabled),
    .workspace-layout.workspace-2d .move-pad [data-move2d="1,-1"]:hover:not(:disabled),
    .workspace-layout.workspace-2d .move-pad [data-move2d="-1,1"]:hover:not(:disabled),
    .workspace-layout.workspace-2d .move-pad [data-move2d="1,1"]:hover:not(:disabled){background:#ede9fe}
    .workspace-layout.workspace-2d .axis-legend{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
    .workspace-layout.workspace-2d .axis-legend span{border:1px solid var(--border);border-radius:7px;padding:4px 7px;font-size:12px;font-weight:650}
    .workspace-layout.workspace-2d .axis-x{color:#b91c1c;background:#fef2f2;border-color:#fecaca!important}
    .workspace-layout.workspace-2d .axis-y{color:#1d4ed8;background:#eff6ff;border-color:#bfdbfe!important}
    .workspace-layout.workspace-2d .axis-diagonal{color:#6d28d9;background:#f5f3ff;border-color:#ddd6fe!important}
    @media(max-width:1100px){
      .workspace-layout.workspace-2d{grid-template-columns:minmax(220px,280px) minmax(0,1fr);gap:10px}
      .workspace-layout.workspace-2d .workspace-rightbar{grid-column:1/-1;display:grid;grid-template-columns:minmax(220px,.75fr) minmax(0,1.25fr);gap:10px;align-items:start}
      .workspace-layout.workspace-2d .workspace-rightbar .workspace-panel{margin:0}
    }
    @media(max-width:700px){
      .workspace-layout.workspace-2d{grid-template-columns:minmax(0,1fr)}
      .workspace-layout.workspace-2d .workspace-stage{grid-column:1;grid-row:1}
      .workspace-layout.workspace-2d .workspace-sidebar{grid-column:1;grid-row:2}
      .workspace-layout.workspace-2d .workspace-rightbar{grid-column:1;grid-row:3;grid-template-columns:minmax(0,1fr)}
      .workspace-layout.workspace-2d .workspace-rightbar .workspace-panel{margin:0 0 10px}
    }
    .workspace-layout.workspace-3d{grid-template-columns:minmax(250px,310px) minmax(0,1fr) minmax(270px,330px)}
    .workspace-layout.workspace-3d .workspace-rightbar{min-width:0}
    .workspace-layout.workspace-3d .workspace-rightbar .workspace-panel{margin:0 0 10px}
    .workspace-layout.workspace-3d .direction-pad{grid-template-columns:repeat(3,minmax(58px,1fr));gap:7px;width:min(100%,245px)}
    .workspace-layout.workspace-3d .direction-pad button{width:100%;padding:8px 5px;font-weight:700}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="-1,0,0"]{grid-column:1;grid-row:1}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="1,0,0"]{grid-column:1;grid-row:2}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,-1,0"]{grid-column:2;grid-row:1}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,1,0"]{grid-column:2;grid-row:2}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,0,1"]{grid-column:3;grid-row:1}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,0,-1"]{grid-column:3;grid-row:2}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="-1,0,0"],
    .workspace-layout.workspace-3d .direction-pad [data-move3d="1,0,0"]{background:#fef2f2;border-color:#fecaca;color:#b91c1c}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="-1,0,0"]:hover:not(:disabled),
    .workspace-layout.workspace-3d .direction-pad [data-move3d="1,0,0"]:hover:not(:disabled){background:#fee2e2}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,-1,0"],
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,1,0"]{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,-1,0"]:hover:not(:disabled),
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,1,0"]:hover:not(:disabled){background:#dbeafe}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,0,1"],
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,0,-1"]{background:#f0fdf4;border-color:#bbf7d0;color:#15803d}
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,0,1"]:hover:not(:disabled),
    .workspace-layout.workspace-3d .direction-pad [data-move3d="0,0,-1"]:hover:not(:disabled){background:#dcfce7}
    @media(max-width:1100px){
      .workspace-layout.workspace-3d{grid-template-columns:minmax(230px,290px) minmax(0,1fr)}
      .workspace-layout.workspace-3d .workspace-rightbar{grid-column:1/-1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
      .workspace-layout.workspace-3d .workspace-rightbar .workspace-panel{margin:0}
    }
    @media(max-width:700px){
      .workspace-layout.workspace-3d{grid-template-columns:minmax(0,1fr)}
      .workspace-layout.workspace-3d .workspace-stage{grid-column:1;grid-row:1}
      .workspace-layout.workspace-3d .workspace-sidebar{grid-column:1;grid-row:2}
      .workspace-layout.workspace-3d .workspace-rightbar{grid-column:1;grid-row:3;grid-template-columns:minmax(0,1fr)}
      .workspace-layout.workspace-3d .workspace-rightbar .workspace-panel{margin:0 0 10px}
    }`;
  document.head.append(layoutStyles);

  let searchPanel = null;
  if (!is3d) {
    const heuristicLabel = document.querySelector('#heuristic')?.closest('label');
    const runButton = document.getElementById('run');
    if (heuristicLabel && runButton) {
      searchPanel = document.createElement('section');
      searchPanel.className = 'panel workspace-panel';
      const heading = document.createElement('strong');
      heading.textContent = '경로 탐색';
      const controls = document.createElement('div');
      controls.className = 'workspace-search-controls';
      controls.append(heuristicLabel, runButton);
      searchPanel.append(heading, controls);
    }

    const gamePanel = panelFor('#game-start');
    const movePad = gamePanel?.querySelector('.move-pad');
    if (movePad && !gamePanel.querySelector('.axis-legend')) {
      const legend = document.createElement('div');
      legend.className = 'axis-legend';
      [['X 좌우', 'axis-x'], ['Y 상하', 'axis-y'], ['대각선 X+Y', 'axis-diagonal']].forEach(([text, className]) => {
        const item = document.createElement('span');
        item.className = className;
        item.textContent = text;
        legend.append(item);
      });
      movePad.before(legend);
    }
  }

  main.insertBefore(workspace, menuPanels[0]);
  workspace.append(sidebar, stage, rightbar);
  leftPanels.forEach(panel => {
    panel.classList.add('workspace-panel');
    sidebar.append(panel);
  });
  if (searchPanel) rightbar.append(searchPanel);
  rightPanels.forEach(panel => {
    panel.classList.add('workspace-panel');
    rightbar.append(panel);
  });
  if (scenePanel) {
    scenePanel.classList.add('workspace-panel');
    stage.append(scenePanel);
  }
  if (statsPanel) {
    statsPanel.classList.add('workspace-panel');
    stage.append(statsPanel);
  }
  if (featurePanel) featurePanel.classList.add('workspace-feature-link');

  if (extras.length) {
    const details = document.createElement('details');
    details.className = 'workspace-extra';
    const summary = document.createElement('summary');
    summary.textContent = is3d ? '추가 정보 및 결과' : '실험 기록 및 추가 정보';
    details.append(summary);
    extras.forEach(panel => details.append(panel));
    main.append(details);
  }

  if (is3d) {
    setNodeAndObstacleOpacity();
    update3dLabels();
  }

  function setNodeAndObstacleOpacity() {
    const canvas = document.getElementById('scene');
    const context = canvas?.getContext('2d');
    if (!context) return;

    const toHex = (r, g, b) => `#${[r, g, b].map(value => Number(value).toString(16).padStart(2, '0')).join('')}`;
    const rgbColor = value => {
      const match = value.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
      return match ? toHex(match[1], match[2], match[3]) : value;
    };
    const obstacleColors = new Set(['#26313e', '#465363', '#344252', '#596778', '#3b4857', '#657487']);
    const nodeColors = new Set(['#f2c94c', '#69b8f2', '#35a66b', '#e45454', '#cbd5e1']);
    const nativeFill = context.fill.bind(context);
    try {
      context.fill = function (...args) {
        const previousAlpha = this.globalAlpha;
        if (previousAlpha === 0.5) {
          const color = rgbColor(String(this.fillStyle).toLowerCase());
          if (obstacleColors.has(color)) this.globalAlpha = 0.7;
          else if (nodeColors.has(color)) this.globalAlpha = 1;
        }
        try {
          return nativeFill(...args);
        } finally {
          this.globalAlpha = previousAlpha;
        }
      };
      // Repaint once so the new alpha values apply to the initial scene too.
      document.getElementById('view-reset')?.click();
    } catch (_) {
      // Keep the page usable if the browser does not allow wrapping this canvas method.
    }
  }

  function update3dLabels() {
    const legend = document.querySelector('.legend');
    if (legend) {
      const labels = legend.querySelectorAll('span');
      if (labels[0]) labels[0].textContent = '⚪ 이동 가능(불투명)';
      if (labels[1]) labels[1].textContent = '⬛ 장애물(30% 투명)';
    }
    const editNote = panelFor('[data-mode]')?.querySelector('.muted.note');
    if (editNote) {
      editNote.textContent = '이동 가능한 노드는 여백을 넓힌 작은 불투명한 점으로 표시하며, 장애물은 약 30% 투명한 입체 블록으로 표시합니다. 장면을 드래그해 회전하고 휠로 확대·축소하세요. 노드를 클릭하면 선택한 도구가 적용됩니다. 투영 화면에서 겹쳐 선택하기 어려운 노드는 시점을 돌려 선택할 수 있습니다.';
    }
  }
})();
