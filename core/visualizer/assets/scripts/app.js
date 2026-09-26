
        let rawNodes = JSON.parse(document.getElementById('data-nodes').textContent);
        let rawEdges = JSON.parse(document.getElementById('data-edges').textContent);
        let rawTree = JSON.parse(document.getElementById('data-tree').textContent);
        let rawFileSources = JSON.parse(document.getElementById('data-sources').textContent);
        let currentNavTab = 'tree';
        let isEditMode = false;
        let currentLoadedFilePath = null;
        let openFolders = new Set(JSON.parse(localStorage.getItem('graf_lens_open_folders') || '[""]'));
        let openEditorTabs = [];
        let previewTabPath = null;
        try {
            openEditorTabs = JSON.parse(localStorage.getItem('graf_open_tabs') || '[]');
        } catch (e) {
            openEditorTabs = [];
        }

        function saveOpenTabsToStorage() {
            try {
                const persistentTabs = openEditorTabs.filter(p => p !== previewTabPath);
                localStorage.setItem('graf_open_tabs', JSON.stringify(persistentTabs));
            } catch (e) {}
        }

        function pinEditorTab(filePath) {
            if (!filePath) return;
            if (previewTabPath === filePath) {
                previewTabPath = null;
                saveOpenTabsToStorage();
                renderEditorTabs();
            }
        }

        function renderEditorTabs() {
            const track = document.getElementById('sublime-tabs-track');
            if (!track) return;

            if (openEditorTabs.length === 0) {
                track.innerHTML = '<div style="color:#75715e; font-size:11px; padding:6px 8px; font-style:italic;">Nenhum arquivo aberto</div>';
                return;
            }

            track.innerHTML = openEditorTabs.map(filePath => {
                const fileName = filePath.split('/').pop();
                const iconInfo = typeof getFileIcon === 'function' ? getFileIcon(fileName) : { icon: '📄' };
                const isActive = filePath === currentLoadedFilePath;
                const isPreview = (filePath === previewTabPath);
                return `
                    <div class="sublime-tab-item ${isActive ? 'active' : ''}" 
                         onclick="switchEditorTab('${filePath}')" 
                         ondblclick="pinEditorTab('${filePath}')" 
                         title="${filePath}${isPreview ? ' (Pré-visualização • Duplo-clique para fixar)' : ''}">
                        <span class="sublime-tab-icon">${iconInfo.icon}</span>
                        <span class="sublime-tab-name ${isPreview ? 'is-preview' : ''}">${fileName}</span>
                        <span class="sublime-tab-close" onclick="closeEditorTab('${filePath}', event)" title="Fechar Aba (Ctrl+W)">✕</span>
                    </div>
                `;
            }).join('');

            if (!track.__wheelBound) {
                track.__wheelBound = true;
                track.addEventListener('wheel', (e) => {
                    if (e.deltaY !== 0) {
                        e.preventDefault();
                        track.scrollLeft += e.deltaY;
                    }
                }, { passive: false });
            }

            const activeEl = track.querySelector('.sublime-tab-item.active');
            if (activeEl) {
                activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
            }
        }

        function openEditorTab(filePath, targetLine, isPreview = false) {
            if (!filePath) return;
            const alreadyOpenIndex = openEditorTabs.indexOf(filePath);

            if (isPreview) {
                if (alreadyOpenIndex !== -1) {
                    // Já aberto (preview ou fixo), apenas mantém
                } else if (previewTabPath && openEditorTabs.includes(previewTabPath)) {
                    const previewIdx = openEditorTabs.indexOf(previewTabPath);
                    openEditorTabs[previewIdx] = filePath;
                    previewTabPath = filePath;
                    saveOpenTabsToStorage();
                } else {
                    openEditorTabs.push(filePath);
                    previewTabPath = filePath;
                    saveOpenTabsToStorage();
                }
            } else {
                if (filePath === previewTabPath) {
                    previewTabPath = null;
                }
                if (alreadyOpenIndex === -1) {
                    openEditorTabs.push(filePath);
                }
                saveOpenTabsToStorage();
            }
            renderEditorTabs();
        }

        function switchEditorTab(filePath) {
            if (filePath === currentLoadedFilePath) return;
            Mediator.loadCode(filePath);
        }

        function closeEditorTab(filePath, event) {
            if (event) event.stopPropagation();
            const index = openEditorTabs.indexOf(filePath);
            if (index === -1) return;

            if (filePath === previewTabPath) {
                previewTabPath = null;
            }
            openEditorTabs.splice(index, 1);
            saveOpenTabsToStorage();

            if (filePath === currentLoadedFilePath) {
                if (openEditorTabs.length > 0) {
                    const nextIndex = Math.min(index, openEditorTabs.length - 1);
                    Mediator.loadCode(openEditorTabs[nextIndex]);
                } else {
                    currentLoadedFilePath = null;
                    const container = document.getElementById('sublime-table-container');
                    const textarea = document.getElementById('sublime-editor-textarea');
                    if (container) {
                        container.innerHTML = '<div style="padding: 24px; color: #75715e; font-family: monospace;">// Nenhuma aba aberta. Selecione um arquivo na árvore ou use Ctrl+P para abrir.</div>';
                    }
                    if (textarea) textarea.value = '';
                    if (cmEditorInstance) cmEditorInstance.getWrapperElement().style.display = 'none';
                    const statusPos = document.getElementById('sublime-status-pos');
                    const statusLang = document.getElementById('sublime-status-lang');
                    if (statusPos) statusPos.innerText = 'Line 0, Column 0';
                    if (statusLang) statusLang.innerText = 'Nenhum arquivo';
                }
            }
            renderEditorTabs();
        }

        function cycleNextTab(direction = 1) {
            if (openEditorTabs.length <= 1) return;
            const currentIndex = openEditorTabs.indexOf(currentLoadedFilePath);
            let nextIndex = (currentIndex + direction + openEditorTabs.length) % openEditorTabs.length;
            Mediator.loadCode(openEditorTabs[nextIndex]);
        }

        function openFile(filePath) {
            Mediator.loadCode(filePath);
        }

        function showToast(message, type = 'info') {
            let toast = document.getElementById('graf-toast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'graf-toast';
                toast.className = 'graf-toast';
                document.body.appendChild(toast);
            }
            toast.className = 'graf-toast' + (type === 'error' ? ' error' : '');
            toast.innerText = message;
            toast.classList.add('show');
            clearTimeout(window.__graf_toast_timeout);
            window.__graf_toast_timeout = setTimeout(() => {
                toast.classList.remove('show');
            }, 2600);
        }

        function applyLiveUpdate(data) {
            if (!data) return;
            try {
                if (data.tree) {
                    rawTree = data.tree;
                    const treeRoot = document.getElementById('tree-root');
                    if (treeRoot) {
                        treeRoot.innerHTML = '';
                        renderTree(rawTree, treeRoot);
                    }
                }
                if (data.sources) {
                    rawFileSources = data.sources;
                }
                if (data.nodes && (typeof nodes !== 'undefined' || window.nodes)) {
                    const targetNodes = typeof nodes !== 'undefined' ? nodes : window.nodes;
                    rawNodes = data.nodes;
                    const currentIds = new Set(data.nodes.map(n => n.id));
                    rawNodes = data.nodes;
                    if (typeof allNodesMap !== 'undefined') {
                        allNodesMap.clear();
                        rawNodes.forEach(n => allNodesMap.set(n.id, n));
                    }
                    if (data.edges) rawEdges = data.edges;
                    if (typeof refreshGraphData === 'function') {
                        refreshGraphData();
                    } else {
                        const existingIds = targetNodes.getIds();
                        const toRemove = existingIds.filter(id => !currentIds.has(id));
                        if (toRemove.length > 0) targetNodes.remove(toRemove);
                        targetNodes.update(data.nodes.map(n => formatVisNode(n)));
                    }
                    if (typeof network !== 'undefined') network.redraw();
                }
                if (data.edges && (typeof edges !== 'undefined' || window.edges)) {
                    rawEdges = data.edges;
                    if (typeof refreshGraphData === 'function') {
                        refreshGraphData();
                    }
                    if (typeof network !== 'undefined') network.redraw();
                }
                if (currentLoadedFilePath && !rawFileSources[currentLoadedFilePath]) {
                    currentLoadedFilePath = null;
                    const textarea = document.getElementById('sublime-editor-textarea');
                    if (textarea) textarea.value = '';
                    const tableContainer = document.getElementById('sublime-table-container');
                    if (tableContainer) {
                        tableContainer.innerHTML = '<div style="padding: 20px; color: #75715e; font-family: monospace;">// Nenhum arquivo selecionado</div>';
                    }
                    const pathEl = document.getElementById('sublime-tab-path');
                    if (pathEl) pathEl.innerText = 'Nenhum arquivo selecionado';
                    const badgeEl = document.getElementById('sublime-git-badge');
                    if (badgeEl) badgeEl.innerHTML = '';
                }
            } catch (err) {
                console.error("Erro ao aplicar live update:", err);
            }
        }

        async function fetchLiveUpdate() {
            try {
                let res = await fetch('/api/data');
                if (!res.ok) res = await fetch('/api/live-data');
                if (!res.ok) return;
                const json = await res.json();
                const payload = json.data || (json.tree ? json : null);
                if (payload) {
                    applyLiveUpdate(payload);
                }
            } catch (e) {}
        }

        const colorMap = {
            "class": "#66d9ef",
            "interface": "#ae81ff",
            "method": "#a6e22e",
            "function": "#a6e22e",
            "file": "#e6db74"
        };

        // 1. Vis.js Network Setup com Células Modulares e Física Pacificada
        const allNodesMap = new Map();
        rawNodes.forEach(n => allNodesMap.set(n.id, n));
        let physicsRunning = false;
        let currentFocusId = null;
        let currentGraphDepth = 1;
        let currentPerspective = 'code'; // 'code' | 'change'
        const GRAPH_NODE_LIMIT = 250;
        let graphLimitExpanded = false;
        let aiTaskStates = {};
        let changeFocusIndex = 0;

        function setGraphDepth(depth) {
            currentGraphDepth = parseInt(depth, 10) || 1;
            refreshGraphData();
        }

        // Mapeia classes contidas em cada arquivo para rotulagem limpa unificada
        const fileClassesMap = new Map();
        rawNodes.filter(n => (n.type === "class" || n.type === "interface" || n.type === "trait") && n.parentId).forEach(c => {
            if (!fileClassesMap.has(c.parentId)) fileClassesMap.set(c.parentId, []);
            fileClassesMap.get(c.parentId).push(c.label);
        });

        function formatVisNode(n, isFocal = false, distance = 0) {
            const classes = fileClassesMap.get(n.id) || [];
            let label = "📁 " + n.label;
            if (classes.length === 1) {
                label = "🏛️ " + classes[0] + "\n📁 " + n.label;
            } else if (classes.length > 1) {
                label = "📁 " + n.label + "\n(" + classes.length + " classes)";
            }
            const hasClasses = classes.length > 0;
            const aiState = aiTaskStates[n.file] || aiTaskStates[n.id];
            const isAiActive = aiState && (aiState === 'creating' || aiState === 'editing');

            // Cores base
            let bgColor = isFocal ? "#272822" : (hasClasses ? "#141414" : "#1a1a1a");
            let borderColor = hasClasses ? "#66d9ef" : "#fd971f";
            let fontColor = isFocal ? "#a6e22e" : (hasClasses ? "#f8f8f2" : "#fd971f");
            let nodeSize = isFocal ? 22 : (hasClasses ? 15 : 11);
            let borderWidth = isFocal ? 4 : 2;

            if (currentPerspective === 'change') {
                if (n.git === "new" || aiState === "creating") {
                    borderColor = "#a6e22e";
                    bgColor = "#182818";
                    fontColor = "#a6e22e";
                    label = (isAiActive ? "⚡ " : "🟢 ") + label;
                    borderWidth = 3.5;
                    nodeSize = Math.max(nodeSize, 16);
                } else if (n.git === "modified" || aiState === "editing") {
                    borderColor = "#fd971f";
                    bgColor = "#281c10";
                    fontColor = "#fd971f";
                    label = (isAiActive ? "⚡ " : "🟠 ") + label;
                    borderWidth = 3.5;
                    nodeSize = Math.max(nodeSize, 16);
                } else if (n.git === "deleted") {
                    borderColor = "#f92672";
                    bgColor = "#281014";
                    fontColor = "#f92672";
                    label = "🔴 " + label;
                    borderWidth = 3.5;
                } else {
                    // Nós não alterados são atenuados no Change Graph para dar foco às alterações
                    borderColor = "#282828";
                    bgColor = "#0d0d0d";
                    fontColor = "#75715e";
                }
            } else {
                // Code Graph
                if (n.git === "new") {
                    borderColor = "#a6e22e";
                    borderWidth = 2.5;
                } else if (n.git === "modified") {
                    borderColor = "#fd971f";
                    borderWidth = 2.5;
                }
            }

            if (isAiActive) {
                borderColor = "#66d9ef";
                borderWidth = 4;
            }

            return {
                id: n.id,
                label: label,
                title: n.title + (classes.length ? "\n🏛️ Classes: " + classes.join(", ") : "") +
                       (isFocal ? "\n🎯 [Elemento em Foco]" : `\n📍 Distância: ${distance}º nível`) +
                       (aiState ? `\n⚡ IA Status: ${aiState.toUpperCase()}` : "") +
                       (n.git ? `\n🌿 Git: ${n.git.toUpperCase()}` : ""),
                color: {
                    background: bgColor,
                    border: borderColor
                },
                borderWidth: borderWidth,
                shape: "dot",
                size: nodeSize,
                shapeProperties: {
                    borderDashes: isAiActive ? [4, 4] : false
                },
                font: {
                    color: fontColor,
                    size: isFocal ? 12 : 10,
                    bold: true,
                    vadjust: 0
                }
            };
        }

        function resolveToGraphNodeId(id) {
            if (!id) return null;
            let current = allNodesMap.get(id);
            if (!current) {
                if (allNodesMap.has(`file://${id}`)) return `file://${id}`;
                return null;
            }
            if (current.type === "file") return current.id;
            if (current.parentId && allNodesMap.has(current.parentId)) {
                return resolveToGraphNodeId(current.parentId);
            }
            if (current.file && allNodesMap.has(`file://${current.file}`)) {
                return `file://${current.file}`;
            }
            return null;
        }

        // Algoritmo de Subgrafo por Vizinhança Adaptativa (Fase 1 ou Fase 2)
        function getNeighborhood(focusId, depth = currentGraphDepth) {
            if (!focusId) {
                const firstFile = rawNodes.find(n => n.type === "file");
                if (firstFile) focusId = firstFile.id;
                else return { focalId: null, nodeIds: new Set(), level1: new Set(), edges: [] };
            }
            const focalGId = resolveToGraphNodeId(focusId);
            if (!focalGId) return { focalId: null, nodeIds: new Set(), level1: new Set(), edges: [] };

            const graphNodeIds = new Set([focalGId]);
            const level1Outbound = new Set();
            const level1Inbound = new Set();

            // Nível 1: Vizinhos diretos (Envio e Recebimento)
            rawEdges.forEach(e => {
                const src = resolveToGraphNodeId(e.source);
                const tgt = resolveToGraphNodeId(e.target);
                if (!src || !tgt || src === tgt) return;
                if (src === focalGId) {
                    level1Outbound.add(tgt);
                    graphNodeIds.add(tgt);
                }
                if (tgt === focalGId) {
                    level1Inbound.add(src);
                    graphNodeIds.add(src);
                }
            });

            const level1All = new Set([...level1Outbound, ...level1Inbound]);

            // Nível 2 (Fase 2): Vizinhos de 2º grau (apenas se depth >= 2)
            if (depth >= 2) {
                rawEdges.forEach(e => {
                    const src = resolveToGraphNodeId(e.source);
                    const tgt = resolveToGraphNodeId(e.target);
                    if (!src || !tgt || src === tgt) return;
                    if (level1All.has(src) && tgt !== focalGId && !level1All.has(tgt)) {
                        graphNodeIds.add(tgt);
                    }
                    if (level1All.has(tgt) && src !== focalGId && !level1All.has(src)) {
                        graphNodeIds.add(src);
                    }
                });
            }

            // Arestas do subgrafo com cores semânticas (Azul = Envio, Laranja = Recebe)
            const edgeAggregator = new Map();
            rawEdges.forEach(e => {
                const src = resolveToGraphNodeId(e.source);
                const tgt = resolveToGraphNodeId(e.target);
                if (!src || !tgt || src === tgt) return;
                if (graphNodeIds.has(src) && graphNodeIds.has(tgt)) {
                    const key = `${src}->${tgt}`;
                    const isOutboundFromFocus = (src === focalGId);
                    const isInboundToFocus = (tgt === focalGId);

                    let edgeColor = "rgba(117, 113, 94, 0.4)";
                    let highlightColor = "#66d9ef";
                    if (isOutboundFromFocus) {
                        edgeColor = "#66d9ef"; // Ciano: Envio
                        highlightColor = "#66d9ef";
                    } else if (isInboundToFocus) {
                        edgeColor = "#fd971f"; // Âmbar: Recebe
                        highlightColor = "#fd971f";
                    }

                    if (!edgeAggregator.has(key)) {
                        edgeAggregator.set(key, {
                            id: key,
                            from: src,
                            to: tgt,
                            arrows: { to: { enabled: true, scaleFactor: 0.75 } },
                            color: { color: edgeColor, highlight: highlightColor, hover: highlightColor, inherit: false },
                            smooth: { enabled: true, type: "continuous", roundness: 0.3 },
                            width: (isOutboundFromFocus || isInboundToFocus) ? 2.2 : 1.2,
                            count: 1
                        });
                    } else {
                        const existing = edgeAggregator.get(key);
                        existing.count++;
                        existing.width = Math.min(3.5, existing.width + 0.3);
                    }
                }
            });
            return { focalId: focalGId, nodeIds: graphNodeIds, level1: level1All, edges: Array.from(edgeAggregator.values()) };
        }

        function getTwoLevelNeighborhood(focusId) {
            return getNeighborhood(focusId, currentGraphDepth);
        }

        function getFilteredNodes() {
            let res = [];
            if (currentPerspective === 'change') {
                // Change Graph: foca nos arquivos alterados e seus vizinhos imediatos
                const changedNodeIds = new Set();
                allNodesMap.forEach(n => {
                    if (n.git || aiTaskStates[n.file] || aiTaskStates[n.id]) {
                        changedNodeIds.add(n.id);
                    }
                });

                if (changedNodeIds.size === 0) {
                    const sub = getNeighborhood(currentFocusId, currentGraphDepth);
                    sub.nodeIds.forEach(nid => {
                        const raw = allNodesMap.get(nid);
                        if (raw) res.push(formatVisNode(raw, nid === sub.focalId, 1));
                    });
                } else {
                    const visibleIds = new Set(changedNodeIds);
                    rawEdges.forEach(e => {
                        if (changedNodeIds.has(e.source)) visibleIds.add(e.target);
                        if (changedNodeIds.has(e.target)) visibleIds.add(e.source);
                    });

                    visibleIds.forEach(nid => {
                        const raw = allNodesMap.get(nid);
                        if (raw) {
                            res.push(formatVisNode(raw, changedNodeIds.has(nid), 0));
                        }
                    });
                }
            } else {
                // Code Graph
                const sub = getNeighborhood(currentFocusId, currentGraphDepth);
                if (!sub.focalId || sub.nodeIds.size === 0) return [];
                currentFocusId = sub.focalId;
                sub.nodeIds.forEach(nid => {
                    const raw = allNodesMap.get(nid);
                    if (raw) {
                        const isFocal = (nid === sub.focalId);
                        const dist = isFocal ? 0 : (sub.level1.has(nid) ? 1 : 2);
                        res.push(formatVisNode(raw, isFocal, dist));
                    }
                });
            }

            // Limite de nós (Fase C: Performance)
            const banner = document.getElementById('graph-limit-banner');
            if (!graphLimitExpanded && res.length > GRAPH_NODE_LIMIT) {
                if (banner) banner.style.display = 'flex';
                res = res.slice(0, GRAPH_NODE_LIMIT);
            } else {
                if (banner) banner.style.display = 'none';
            }

            return res;
        }

        function getFilteredEdges() {
            if (currentPerspective === 'change') {
                const currentVisibleIds = new Set(getFilteredNodes().map(n => n.id));
                const resEdges = [];
                rawEdges.forEach(e => {
                    if (currentVisibleIds.has(e.source) && currentVisibleIds.has(e.target)) {
                        resEdges.push({
                            id: `${e.source}->${e.target}`,
                            from: e.source,
                            to: e.target,
                            arrows: "to",
                            color: { color: "rgba(255,255,255,0.18)", highlight: "#66d9ef" },
                            width: 1.2
                        });
                    }
                });
                return resEdges;
            }
            const sub = getNeighborhood(currentFocusId, currentGraphDepth);
            return sub.edges;
        }

        let nodes = new vis.DataSet([]);
        let edges = new vis.DataSet([]);
        let network = null;

        // Inicialização Assíncrona Não-Bloqueante do Grafo (libera Árvore e Editor imediatamente)
        function initGraphAsync() {
            const container = document.getElementById('network');
            nodes = new vis.DataSet(getFilteredNodes());
            edges = new vis.DataSet(getFilteredEdges());
            window.nodes = nodes;
            window.edges = edges;

            network = new vis.Network(container, { nodes, edges }, {
                interaction: { hover: true, tooltipDelay: 50, selectConnectedEdges: true, hideEdgesOnDrag: true },
                edges: { selectionWidth: 2.2, hoverWidth: 1.1 },
                physics: {
                    enabled: true,
                    solver: "barnesHut",
                    barnesHut: {
                        gravitationalConstant: -6000,
                        centralGravity: 0.08,
                        springLength: 260,
                        springConstant: 0.015,
                        damping: 0.90,
                        avoidOverlap: 1.0
                    },
                    stabilization: { iterations: 40, updateInterval: 10 }
                }
            });
            window.network = network;

            network.once('stabilizationIterationsDone', () => {
                network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
            });

            // 1 Clique no Grafo: Apenas consulta e inspeção de dependências (mantém código e árvore intactos)
            network.on('click', (params) => {
                if (params.nodes && params.nodes.length > 0) {
                    const clickedId = params.nodes[0];
                    Mediator.inspectOnly(clickedId);
                }
            });

            // 2 Cliques no Grafo: Troca ativa de contexto (abre o arquivo no editor e foca na árvore)
            network.on('doubleClick', (params) => {
                if (params.nodes && params.nodes.length > 0) {
                    Mediator.select(params.nodes[0], 'network');
                }
            });

            updateNodesCount();
        }
        setTimeout(initGraphAsync, 0);

        function refreshGraphData() {
            const newNodes = getFilteredNodes();
            nodes.clear();
            nodes.add(newNodes);
            edges.clear();
            edges.add(getFilteredEdges());
            updateNodesCount();
            network.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
        }

        window.switchPerspective = function(mode) {
            currentPerspective = mode;
            document.querySelectorAll('.perspective-tab').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById(`btn-perspective-${mode}`);
            if (activeBtn) activeBtn.classList.add('active');

            const changeBanner = document.getElementById('change-summary-banner');
            const changeMiniMap = document.getElementById('change-mini-map');
            if (changeBanner) {
                if (mode === 'change') {
                    changeBanner.style.display = 'flex';
                    if (changeMiniMap) changeMiniMap.style.display = 'flex';
                    updateChangeSummaryStats();
                    updateChangeMiniMap();
                } else {
                    changeBanner.style.display = 'none';
                    if (changeMiniMap) changeMiniMap.style.display = 'none';
                }
            }

            refreshGraphData();
            showToast(`Perspectiva alterada para: ${mode.toUpperCase()}`, 'info');
        };

        window.expandGraphLimit = function() {
            graphLimitExpanded = true;
            const banner = document.getElementById('graph-limit-banner');
            if (banner) banner.style.display = 'none';
            refreshGraphData();
            showToast("Visualização expandida para todos os nós.", "info");
        };

        window.focusNextChange = function() {
            const altered = Array.from(allNodesMap.values()).filter(n => n.git || aiTaskStates[n.file] || aiTaskStates[n.id]);
            if (altered.length === 0) {
                showToast("Nenhuma alteração ativa no momento.", "info");
                return;
            }
            changeFocusIndex = (changeFocusIndex + 1) % altered.length;
            const target = altered[changeFocusIndex];
            const graphId = resolveToGraphNodeId(target.id);
            if (graphId && network) {
                network.focus(graphId, { scale: 1.25, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
                Mediator.inspectOnly(graphId);
            }
        };

        window.focusPreviousChange = function() {
            const altered = Array.from(allNodesMap.values()).filter(n => n.git || aiTaskStates[n.file] || aiTaskStates[n.id]);
            if (altered.length === 0) {
                showToast("Nenhuma alteração ativa no momento.", "info");
                return;
            }
            changeFocusIndex = (changeFocusIndex - 1 + altered.length) % altered.length;
            const target = altered[changeFocusIndex];
            const graphId = resolveToGraphNodeId(target.id);
            if (graphId && network) {
                network.focus(graphId, { scale: 1.25, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
                Mediator.inspectOnly(graphId);
            }
        };

        function updateChangeSummaryStats() {
            const filesMap = new Map();
            allNodesMap.forEach(n => {
                if (!n.file) return;
                let status = null;
                if (n.git === 'new' || aiTaskStates[n.file] === 'creating') status = 'new';
                else if (n.git === 'modified' || aiTaskStates[n.file] === 'editing') status = 'mod';
                else if (n.git === 'deleted') status = 'del';
                if (status && !filesMap.has(n.file)) {
                    filesMap.set(n.file, { file: n.file, status: status, graphId: resolveToGraphNodeId(n.id) });
                }
            });

            let nNew = 0, nMod = 0, nDel = 0;
            filesMap.forEach(item => {
                if (item.status === 'new') nNew++;
                else if (item.status === 'mod') nMod++;
                else if (item.status === 'del') nDel++;
            });

            const statNew = document.getElementById('stat-new');
            const statMod = document.getElementById('stat-mod');
            const statDel = document.getElementById('stat-del');
            const badge = document.getElementById('change-badge');

            if (statNew) statNew.innerText = `● ${nNew} novos`;
            if (statMod) statMod.innerText = `● ${nMod} modificados`;
            if (statDel) statDel.innerText = `● ${nDel} excluídos`;

            const total = nNew + nMod + nDel;
            if (badge) {
                badge.innerText = total;
                badge.style.display = total > 0 ? 'inline-block' : 'none';
            }
            updateChangeMiniMap(filesMap);
        }

        let isMiniMapExpanded = false;
        window.toggleMiniMapExpansion = function() {
            isMiniMapExpanded = !isMiniMapExpanded;
            const container = document.getElementById('mini-map-files-container');
            const btn = document.getElementById('btn-toggle-mini-map');
            if (container) container.style.display = isMiniMapExpanded ? 'flex' : 'none';
            if (btn) btn.classList.toggle('open', isMiniMapExpanded);
        };

        function updateChangeMiniMap(filesMap) {
            if (!filesMap) {
                filesMap = new Map();
                allNodesMap.forEach(n => {
                    if (!n.file) return;
                    let status = null;
                    if (n.git === 'new' || aiTaskStates[n.file] === 'creating') status = 'new';
                    else if (n.git === 'modified' || aiTaskStates[n.file] === 'editing') status = 'mod';
                    else if (n.git === 'deleted') status = 'del';
                    if (status && !filesMap.has(n.file)) {
                        filesMap.set(n.file, { file: n.file, status: status, graphId: resolveToGraphNodeId(n.id) });
                    }
                });
            }
            let nNew = 0, nMod = 0, nDel = 0;
            const changedFiles = Array.from(filesMap.values());
            changedFiles.forEach(item => {
                if (item.status === 'new') nNew++;
                else if (item.status === 'mod') nMod++;
                else if (item.status === 'del') nDel++;
            });
            const total = changedFiles.length;
            const summaryText = document.getElementById('mini-map-summary-text');
            if (summaryText) {
                summaryText.innerText = `${total} mutações ativas`;
            }
            const barNew = document.getElementById('bar-new');
            const barMod = document.getElementById('bar-mod');
            const barDel = document.getElementById('bar-del');
            if (total === 0) {
                if (barNew) barNew.style.width = '0%';
                if (barMod) barMod.style.width = '0%';
                if (barDel) barDel.style.width = '0%';
            } else {
                if (barNew) barNew.style.width = `${(nNew / total) * 100}%`;
                if (barMod) barMod.style.width = `${(nMod / total) * 100}%`;
                if (barDel) barDel.style.width = `${(nDel / total) * 100}%`;
            }

            // Renderiza lista interativa de arquivos com cores semânticas (deduplicada)
            const filesContainer = document.getElementById('mini-map-files-container');
            if (filesContainer) {
                if (changedFiles.length === 0) {
                    filesContainer.innerHTML = '<div style="color:#75715e; font-size:10px; padding:4px; text-align:center;">Nenhum arquivo modificado</div>';
                } else {
                    filesContainer.innerHTML = changedFiles.map(item => {
                        const fileName = item.file.split('/').pop();
                        const color = item.status === 'new' ? '#a6e22e' : (item.status === 'mod' ? '#fd971f' : '#f92672');
                        const tagText = item.status === 'new' ? 'NEW' : (item.status === 'mod' ? 'MOD' : 'DEL');
                        const graphId = item.graphId;
                        return `
                            <div class="mini-map-file-row" onclick="Mediator.loadCode('${item.file}', 1); if (network && '${graphId}') { network.focus('${graphId}', { scale: 1.25, animation: { duration: 350 } }); Mediator.inspectOnly('${graphId}'); }" title="${item.file} (Clique para abrir e focar)">
                                <span class="mini-map-file-name">📄 ${fileName}</span>
                                <span style="color:${color}; font-weight:bold; font-size:9.5px; border:1px solid ${color}44; padding:1px 4px; border-radius:3px;">${tagText}</span>
                            </div>
                        `;
                    }).join('');
                }
            }
        }

        // 13. Gaveta Retrátil de Histórico de Operações da IA (Fase E.3)
        function updateNodesCount() {
            const badge = document.getElementById('graph-nodes-count');
            if (badge) badge.innerText = `${nodes.length} nós ativos`;
            const footerNodes = document.getElementById('footer-nodes-count');
            if (footerNodes) footerNodes.innerText = `${allNodesMap.size} nós`;
            const footerEdges = document.getElementById('footer-edges-count');
            if (footerEdges) footerEdges.innerText = `${rawEdges.length} conexões`;
        }
        updateNodesCount();

        // 2. Construtor da Tabela de Código Monokai Sublime
        function buildSublimeTable(highlightedHtml, targetLine) {
            const lines = highlightedHtml.split('\n');
            let openTags = [];
            let tableHtml = '<table class="sublime-table">';
            
            for (let i = 0; i < lines.length; i++) {
                const lineNum = i + 1;
                const isTarget = (lineNum === targetLine);
                const lineContent = lines[i];
                
                const prefix = openTags.map(t => t.full).join('');
                
                const tagRegex = /<\/?([a-z0-9_-]+)([^>]*)>/gi;
                let match;
                while ((match = tagRegex.exec(lineContent)) !== null) {
                    const isClosing = match[0].startsWith('</');
                    const tagName = match[1];
                    if (isClosing) {
                        openTags.pop();
                    } else {
                        openTags.push({ name: tagName, full: match[0] });
                    }
                }
                
                const suffix = openTags.slice().reverse().map(t => `</${t.name}>`).join('');
                const fullLine = prefix + lineContent + suffix;
                const renderContent = (fullLine && fullLine.trim().length > 0) ? fullLine : '&nbsp;';
                
                const rowClass = isTarget ? 'active-sublime-line' : '';
                tableHtml += `
                    <tr class="${rowClass}" id="L${lineNum}">
                        <td class="sublime-gutter">${lineNum}</td>
                        <td class="sublime-code-cell">${renderContent}</td>
                    </tr>
                `;
            }
            tableHtml += '</table>';
            return tableHtml;
        }

        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // Formata identificadores de conexão para exibição limpa (apenas nome do arquivo/símbolo)
        function formatConnLabel(id) {
            if (!id) return '';
            if (id.includes('::')) {
                const parts = id.split('::');
                const file = parts[0].split('/').pop();
                const symbol = parts.slice(1).join('::');
                return `${file} ➔ ${symbol}`;
            }
            return '📄 ' + id.split('/').pop();
        }

        // 3. Mediator Pattern (Sincronização Bidirecional)
        const Mediator = {
            selectedId: null,
            currentNode: null,

            // Inspeção sem alteração do editor nem da árvore de arquivos
            inspectOnly(nodeId) {
                if (!nodeId) return;
                const node = allNodesMap.get(nodeId) || rawNodes.find(n => n.id === nodeId);
                if (node) {
                    this.currentNode = node;
                    this.updateInspector(node.id);
                }
            },

            select(nodeId, origin, targetLine, isPreview = false) {
                if (!nodeId) return;
                this.selectedId = nodeId;
                this.currentNode = rawNodes.find(n => n.id === nodeId);

                // A. Sincroniza o Grafo Vis.js (Subgrafo de 2 níveis focado no elemento)
                const targetGraphId = resolveToGraphNodeId(nodeId);
                if (targetGraphId && targetGraphId !== currentFocusId) {
                    currentFocusId = targetGraphId;
                    refreshGraphData();
                } else if (targetGraphId && origin !== 'network') {
                    network.selectNodes([targetGraphId]);
                    network.focus(targetGraphId, {
                        scale: 1.1,
                        animation: { duration: 300, easingFunction: 'easeInOutQuad' }
                    });
                }

                // B. Sincroniza a Árvore de Arquivos
                if (origin !== 'tree') {
                    this.highlightInTree(nodeId);
                }

                // C. Atualiza o Inspetor de Métricas
                try {
                    this.updateInspector(nodeId);
                } catch (e) {
                    console.error("Erro no updateInspector:", e);
                }

                // D. Carrega o Código no Editor Monokai
                if (this.currentNode) {
                    this.loadCode(this.currentNode.file, targetLine || this.currentNode.line, isPreview);
                }
            },

            highlightInTree(nodeId) {
                document.querySelectorAll('.tree-row, .tree-symbol-row').forEach(el => el.classList.remove('active'));
                
                document.querySelectorAll(`[data-id="${CSS.escape(nodeId)}"]`).forEach(targetEl => {
                    targetEl.classList.add('active');
                    let parent = targetEl.closest('.tree-children');
                    while (parent) {
                        parent.classList.add('open');
                        const arrow = parent.previousElementSibling?.querySelector('.tree-arrow');
                        if (arrow) arrow.classList.add('open');
                        parent = parent.parentElement.closest('.tree-children');
                    }
                    targetEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                });
            },

            updateInspector(nodeId) {
                const node = this.currentNode;
                const placeholder = document.getElementById('inspector-placeholder');
                const content = document.getElementById('inspector-content');

                if (!node) {
                    placeholder.style.display = 'block';
                    content.style.display = 'none';
                    return;
                }

                placeholder.style.display = 'none';
                content.style.display = 'flex';

                document.getElementById('det-ca').innerText = node.ca;
                document.getElementById('det-ce').innerText = node.ce;
                document.getElementById('det-inst').innerText = node.instability;

                // Inbound (quem chama)
                const inboundList = document.getElementById('det-inbound');
                inboundList.innerHTML = '';
                const callers = rawEdges.filter(e => e.target === nodeId);
                if (callers.length === 0) {
                    inboundList.innerHTML = '<span style="color:#75715e;font-size:12px;">Nenhum chamador direto.</span>';
                } else {
                    callers.forEach(c => {
                        const item = document.createElement('div');
                        item.className = 'conn-item';
                        item.innerText = formatConnLabel(c.source);
                        item.title = c.source;
                        item.onclick = () => Mediator.select(c.source, 'inspector');
                        inboundList.appendChild(item);
                    });
                }

                // Outbound (de quem depende)
                const outboundList = document.getElementById('det-outbound');
                outboundList.innerHTML = '';
                const callees = rawEdges.filter(e => e.source === nodeId);
                if (callees.length === 0) {
                    outboundList.innerHTML = '<span style="color:#75715e;font-size:12px;">Nenhuma dependência externa direta.</span>';
                } else {
                    callees.forEach(c => {
                        const item = document.createElement('div');
                        item.className = 'conn-item';
                        item.innerText = formatConnLabel(c.target);
                        item.title = c.target;
                        item.onclick = () => Mediator.select(c.target, 'inspector');
                        outboundList.appendChild(item);
                    });
                }
            },

            async loadCode(filePath, targetLine, isPreview = false) {
                currentLoadedFilePath = filePath;
                const container = document.getElementById('sublime-table-container');
                const textarea = document.getElementById('sublime-editor-textarea');
                const statusPos = document.getElementById('sublime-status-pos');
                const statusLang = document.getElementById('sublime-status-lang');

                if (!filePath) {
                    container.innerHTML = '<div style="padding: 20px; color: #75715e;">// Nenhum arquivo selecionado.</div>';
                    if (textarea) textarea.value = '';
                    renderEditorTabs();
                    return;
                }

                openEditorTab(filePath, targetLine, isPreview);
                const fileName = filePath.split('/').pop();

                // Lazy Loading: busca do cache local ou via API sob demanda
                let source = rawFileSources[filePath];
                if (source === undefined) {
                    container.innerHTML = `<div style="padding: 20px; color: #66d9ef; font-family: monospace;">⚡ Carregando ${fileName} sob demanda...</div>`;
                    try {
                        let res = await fetch(`/api/file-content?path=${encodeURIComponent(filePath)}`);
                        if (!res.ok) {
                            res = await fetch('/api/file-content', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ path: filePath })
                            });
                        }
                        if (res.ok) {
                            const json = await res.json();
                            if (json.success && json.content !== undefined) {
                                source = json.content;
                                rawFileSources[filePath] = source;
                            }
                        }
                    } catch (e) {}
                }

                if (source === undefined) {
                    container.innerHTML = '<div style="padding: 20px; color: #f92672;">// Arquivo não pôde ser carregado.</div>';
                    if (textarea) textarea.value = '';
                    return;
                }
                if (textarea) textarea.value = source;
                if (cmEditorInstance && isEditMode) {
                    cmEditorInstance.setOption('mode', getCodeMirrorMode(filePath));
                    cmEditorInstance.setValue(source);
                }

                let lang = 'python';
                let langLabel = 'Python';
                if (filePath.endsWith('.php')) { lang = 'php'; langLabel = 'PHP'; }
                else if (filePath.endsWith('.js') || filePath.endsWith('.jsx')) { lang = 'javascript'; langLabel = 'JavaScript'; }
                else if (filePath.endsWith('.ts') || filePath.endsWith('.tsx')) { lang = 'typescript'; langLabel = 'TypeScript'; }
                else if (filePath.endsWith('.html') || filePath.endsWith('.blade.php')) { lang = 'html'; langLabel = 'HTML / Blade'; }
                else if (filePath.endsWith('.md')) { lang = 'markdown'; langLabel = 'Markdown'; }
                else if (filePath.endsWith('.json')) { lang = 'json'; langLabel = 'JSON'; }
                else if (filePath.endsWith('.css') || filePath.endsWith('.scss')) { lang = 'css'; langLabel = 'CSS'; }
                else if (filePath.endsWith('.yaml') || filePath.endsWith('.yml')) { lang = 'yaml'; langLabel = 'YAML'; }
                else if (filePath.endsWith('.sh') || filePath.endsWith('.bash') || filePath.endsWith('.zsh')) { lang = 'bash'; langLabel = 'Shell Script'; }
                else if (filePath.endsWith('.sql')) { lang = 'sql'; langLabel = 'SQL'; }
                else if (filePath.endsWith('.xml') || filePath.endsWith('.svg')) { lang = 'xml'; langLabel = 'XML'; }

                statusPos.innerText = `Line ${targetLine || 1}, Column 1`;
                statusLang.innerText = isEditMode ? `UTF-8 | ${langLabel} (Modo Edição • Ctrl+S para Salvar)` : `UTF-8 | ${langLabel}`;

                let highlightedHtml = '';
                try {
                    if (window.hljs) {
                        highlightedHtml = hljs.highlight(source, { language: lang, ignoreIllegals: true }).value;
                    } else {
                        highlightedHtml = escapeHtml(source);
                    }
                } catch (e) {
                    highlightedHtml = escapeHtml(source);
                }

                container.innerHTML = buildSublimeTable(highlightedHtml, targetLine);

                if (targetLine && targetLine > 0) {
                    setTimeout(() => {
                        const row = document.getElementById(`L${targetLine}`);
                        if (row) {
                            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }, 60);
                }
            }
        };

        function copyAgentPrompt() {
            const node = Mediator.currentNode;
            if (!node) {
                showToast('⚠️ Selecione um arquivo ou classe para copiar o contexto.', 'error');
                return;
            }
            const callers = rawEdges.filter(e => e.target === node.id).map(e => formatConnLabel(e.source)).join(', ') || 'Nenhum chamador direto';
            const callees = rawEdges.filter(e => e.source === node.id).map(e => formatConnLabel(e.target)).join(', ') || 'Nenhuma dependência externa';
            
            const promptText = `# 🤖 Contexto Arquitetural para o Agente\n\n` +
                `- **Componente Alvo:** ${node.label} (${node.type.toUpperCase()})\n` +
                `- **Arquivo:** ${node.file}:${node.line}\n` +
                `- **Git Status:** ${node.git === 'new' ? 'Novo (não rastreado)' : (node.git === 'modified' ? 'Modificado' : 'Rastreado / Inalterado')}\n` +
                `- **Descrição / Doc:** ${node.doc || 'Sem docstring registrada'}\n` +
                `- **Acoplamento Aferente (Ca - Chamado por):** ${node.ca} [${callers}]\n` +
                `- **Acoplamento Eferente (Ce - Depende de):** ${node.ce} [${callees}]\n` +
                `- **Instabilidade (I = Ce / (Ca + Ce)):** ${node.instability}\n\n` +
                `## 🎯 Diretrizes para Execução:\n` +
                `1. Mantenha as regras de Arquitetura Limpa, Clean Code e SOLID.\n` +
                `2. Não quebre os chamadores listados acima.\n` +
                `3. Escreva testes unitários para validar qualquer alteração.\n`;

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(promptText).then(() => {
                    showToast('📋 Prompt arquitetural copiado com sucesso! Pronto para colar no seu agente.');
                }).catch(() => {
                    window.prompt('Copie o prompt abaixo:', promptText);
                });
            } else {
                window.prompt('Copie o prompt abaixo:', promptText);
            }
        }

        // Resolução de Ícones Temáticos por Extensão e Tipo de Pasta
        function getFileIcon(fileName) {
            const lower = fileName.toLowerCase();
            if (lower === '.gitignore' || lower === '.gitattributes') return { icon: '📙', color: '#fd971f' };
            if (lower.startsWith('.env')) return { icon: '🔒', color: '#e6db74' };
            if (lower === '.editorconfig') return { icon: '⚙️', color: '#a6e22e' };
            if (lower === '.htaccess') return { icon: '🛡️', color: '#ae81ff' };
            if (lower === 'artisan') return { icon: '⚡', color: '#f92672' };
            if (lower.startsWith('composer')) return { icon: '🎼', color: '#66d9ef' };
            if (lower === 'package.json' || lower === 'package-lock.json') return { icon: '📦', color: '#f92672' };
            if (lower.endsWith('.php') || lower.endsWith('.blade.php')) return { icon: '🐘', color: '#8892be' };
            if (lower.endsWith('.py')) return { icon: '🐍', color: '#66d9ef' };
            if (lower.endsWith('.js') || lower.endsWith('.jsx')) return { icon: '🟨', color: '#e6db74' };
            if (lower.endsWith('.ts') || lower.endsWith('.tsx')) return { icon: '🟦', color: '#66d9ef' };
            if (lower.endsWith('.html')) return { icon: '🌐', color: '#fd971f' };
            if (lower.endsWith('.css') || lower.endsWith('.scss')) return { icon: '🎨', color: '#66d9ef' };
            if (lower.endsWith('.json')) return { icon: '📋', color: '#e6db74' };
            if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return { icon: '📑', color: '#f92672' };
            if (lower.endsWith('.md')) return { icon: 'Ⓜ️', color: '#66d9ef' };
            if (lower.endsWith('.sh') || lower.endsWith('.bash') || lower.endsWith('.zsh')) return { icon: '🐚', color: '#a6e22e' };
            if (lower.endsWith('.sql')) return { icon: '🗄️', color: '#e6db74' };
            if (lower.endsWith('.xml')) return { icon: '📰', color: '#fd971f' };
            if (lower.endsWith('.lock')) return { icon: '🔒', color: '#75715e' };
            return { icon: '📄', color: '#f8f8f2' };
        }

        function getFolderIcon(folderName, isOpen) {
            const lower = folderName.toLowerCase();
            if (lower === '.idea' || lower === '.vscode') return '💡';
            if (lower === 'tests' || lower === 'test') return '🧪';
            if (lower === 'doc' || lower === 'docs' || lower === 'docs-internas') return '📚';
            if (lower === 'app' || lower === 'src' || lower === 'core') return '📦';
            if (lower === 'database') return '🗄️';
            if (lower === 'config') return '⚙️';
            if (lower === 'public') return '🌐';
            if (lower === 'storage') return '💾';
            return isOpen ? '📂' : '📁';
        }

        // 4. Renderização da Árvore (Composite Pattern)
        function renderTree(comp, parentEl) {
            if (comp.type === 'directory') {
                const dirDiv = document.createElement('div');
                dirDiv.className = 'tree-node';

                const isOpen = openFolders.has(comp.relative_path) || comp.relative_path === '' || openFolders.size === 0;

                const row = document.createElement('div');
                row.className = 'tree-row';

                const arrow = document.createElement('span');
                arrow.className = 'tree-arrow' + (isOpen ? ' open' : '');
                arrow.innerText = '▶';

                const icon = document.createElement('span');
                icon.innerText = getFolderIcon(comp.name, isOpen);

                row.onclick = (e) => {
                    e.stopPropagation();
                    const childrenEl = dirDiv.querySelector('.tree-children');
                    if (childrenEl) {
                        const opened = childrenEl.classList.toggle('open');
                        arrow.classList.toggle('open');
                        icon.innerText = getFolderIcon(comp.name, opened);
                        if (opened) {
                            openFolders.add(comp.relative_path);
                        } else {
                            openFolders.delete(comp.relative_path);
                        }
                        try {
                            localStorage.setItem('graf_lens_open_folders', JSON.stringify(Array.from(openFolders)));
                        } catch (err) {}
                    }
                };

                const name = document.createElement('span');
                name.innerText = comp.name;

                row.appendChild(arrow);
                row.appendChild(icon);
                row.appendChild(name);

                const dirActionsBtn = document.createElement('button');
                dirActionsBtn.className = 'tree-add-btn';
                dirActionsBtn.title = `Criar ou gerenciar em "${comp.name}"`;
                dirActionsBtn.innerText = '+';
                dirActionsBtn.onclick = (e) => {
                    e.stopPropagation();
                    openTreeContextMenu(e, 'directory', comp.relative_path, comp.name);
                };
                row.appendChild(dirActionsBtn);

                dirDiv.appendChild(row);

                const childrenDiv = document.createElement('div');
                childrenDiv.className = 'tree-children' + (isOpen ? ' open' : '');
                comp.children.forEach(child => renderTree(child, childrenDiv));
                dirDiv.appendChild(childrenDiv);

                parentEl.appendChild(dirDiv);
            } else if (comp.type === 'file') {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'tree-node';

                const row = document.createElement('div');
                row.className = 'tree-row';
                row.setAttribute('data-id', comp.full_id);
                row.onclick = (e) => {
                    e.stopPropagation();
                    Mediator.select(comp.full_id, 'tree', null, true);
                };
                row.ondblclick = (e) => {
                    e.stopPropagation();
                    pinEditorTab(comp.relative_path);
                };

                const spacer = document.createElement('span');
                spacer.style.width = '10px';

                const fileInfo = getFileIcon(comp.name);
                const icon = document.createElement('span');
                icon.innerText = fileInfo.icon;
                icon.title = comp.name;

                const name = document.createElement('span');
                name.className = 'tree-file-name';
                name.innerText = comp.name;

                row.appendChild(spacer);
                row.appendChild(icon);
                row.appendChild(name);

                if (comp.git_status) {
                    const gitBadge = document.createElement('span');
                    if (comp.git_status === 'new') {
                        gitBadge.className = 'git-badge git-badge-new';
                        gitBadge.innerText = '+ Novo';
                    } else if (comp.git_status === 'modified') {
                        gitBadge.className = 'git-badge git-badge-mod';
                        gitBadge.innerText = '~ Mod';
                    } else if (comp.git_status === 'deleted') {
                        gitBadge.className = 'git-badge git-badge-del';
                        gitBadge.innerText = '- Rem';
                    }
                    row.appendChild(gitBadge);
                }

                if (comp.symbols && comp.symbols.length > 0) {
                    const badge = document.createElement('span');
                    badge.className = 'badge-count';
                    badge.innerText = comp.symbols.length;
                    row.appendChild(badge);
                }

                const fileActionsBtn = document.createElement('button');
                fileActionsBtn.className = 'tree-more-btn';
                fileActionsBtn.title = `Ações em "${comp.name}" (Renomear, Excluir)`;
                fileActionsBtn.innerText = '⋮';
                fileActionsBtn.onclick = (e) => {
                    e.stopPropagation();
                    openTreeContextMenu(e, 'file', comp.relative_path, comp.name);
                };
                row.appendChild(fileActionsBtn);

                fileDiv.appendChild(row);

                if (comp.symbols && comp.symbols.length > 0) {
                    const symContainer = document.createElement('div');
                    symContainer.className = 'tree-children';
                    comp.symbols.forEach(sym => {
                        const symRow = document.createElement('div');
                        symRow.className = 'tree-symbol-row';
                        symRow.setAttribute('data-id', sym.id);
                        symRow.onclick = (e) => {
                            e.stopPropagation();
                            Mediator.select(sym.id, 'tree', null, true);
                        };
                        symRow.ondblclick = (e) => {
                            e.stopPropagation();
                            pinEditorTab(comp.relative_path);
                        };
                        const symIcon = sym.type === 'class' ? '🏛️' : (sym.type === 'interface' ? '📜' : '⚡');
                        symRow.innerHTML = `<span>${symIcon}</span> <span>${sym.name}</span>`;
                        symContainer.appendChild(symRow);
                    });
                    fileDiv.appendChild(symContainer);

                    row.ondblclick = (e) => {
                        e.stopPropagation();
                        pinEditorTab(comp.relative_path);
                        symContainer.classList.toggle('open');
                    };
                }

                parentEl.appendChild(fileDiv);
            }
        }

        // Inicializa a árvore
        const treeRoot = document.getElementById('tree-root');
        renderTree(rawTree, treeRoot);

        // Auto-carrega as abas da sessão anterior ou o primeiro arquivo
        function autoLoadInitialFile() {
            if (openEditorTabs.length > 0) {
                const lastTab = openEditorTabs[openEditorTabs.length - 1];
                renderEditorTabs();
                Mediator.loadCode(lastTab, 1);
            } else {
                const firstFile = rawNodes.find(n => n.type === 'file' && n.file);
                if (firstFile) {
                    Mediator.loadCode(firstFile.file, 1);
                    Mediator.highlightInTree(firstFile.id);
                }
            }
        }
        autoLoadInitialFile();

        // 5.1. Função para recolher/retrair todas as pastas e símbolos da árvore
        function collapseAllFolders() {
            openFolders.clear();
            try {
                localStorage.setItem('graf_lens_open_folders', JSON.stringify([]));
            } catch (e) {}

            const rootNode = document.querySelector('#tree-root > .tree-node');
            if (rootNode) {
                rootNode.querySelectorAll('.tree-children').forEach((childEl, idx) => {
                    if (idx > 0) childEl.classList.remove('open');
                });
                // Atualiza APENAS as linhas que são pastas (possuem .tree-arrow)
                rootNode.querySelectorAll('.tree-row').forEach((row, idx) => {
                    const arrow = row.querySelector('.tree-arrow');
                    if (arrow && idx > 0) {
                        arrow.classList.remove('open');
                        const icon = row.querySelector('span:nth-child(2)');
                        const nameEl = row.querySelector('span:nth-child(3)');
                        if (icon && nameEl) {
                            icon.innerText = getFolderIcon(nameEl.innerText, false);
                        }
                    }
                });
            }
            showToast('📁 Todas as pastas foram recolhidas');
        }


        // 6. Sub-abas de Navegação (Árvore vs Inspetor)
        function switchNavTab(tab) {
            currentNavTab = tab;
            document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('nav-pane-tree').style.display = 'none';
            document.getElementById('nav-pane-inspector').style.display = 'none';

            if (tab === 'tree') {
                document.getElementById('subtab-btn-tree').classList.add('active');
                document.getElementById('nav-pane-tree').style.display = 'flex';
            } else {
                document.getElementById('subtab-btn-inspector').classList.add('active');
                document.getElementById('nav-pane-inspector').style.display = 'flex';
            }
        }

        // Alterna visibilidade do Sub-Painel de Navegação
        function toggleNavSubpanel() {
            const nav = document.getElementById('nav-subpanel');
            const resizer = document.getElementById('internal-resizer');
            const btnReopen = document.getElementById('btn-reopen-nav');
            
            nav.classList.toggle('hidden');
            const isHidden = nav.classList.contains('hidden');
            resizer.style.display = isHidden ? 'none' : 'block';
            btnReopen.style.display = isHidden ? 'inline-flex' : 'none';
        }

        // 7. Alterna visibilidade do Sub-Painel de Código (Recolher / Expandir)
        let isCodeCollapsed = false;
        let savedSidebarWidthBeforeCollapse = null;

        function toggleCodeSubpanel(forceState) {
            const workspaceBody = document.querySelector('.workspace-body');
            const btnStage = document.getElementById('btn-collapse-stage');
            const btnNavReopenCode = document.getElementById('btn-nav-reopen-code');
            const sidebar = document.getElementById('sidebar');

            if (typeof forceState === 'boolean') {
                isCodeCollapsed = forceState;
            } else {
                isCodeCollapsed = !isCodeCollapsed;
            }

            if (isCodeCollapsed) {
                workspaceBody.classList.add('code-collapsed');
                if (btnNavReopenCode) btnNavReopenCode.style.display = 'inline-flex';
                if (btnStage) {
                    btnStage.innerHTML = '▶';
                    btnStage.title = 'Mostrar Editor de Código';
                }
                savedSidebarWidthBeforeCollapse = sidebar.offsetWidth;
                updateSidebarWidth(Math.max(280, Math.min(savedSidebarWidthBeforeCollapse, 360)));
            } else {
                workspaceBody.classList.remove('code-collapsed');
                if (btnNavReopenCode) btnNavReopenCode.style.display = 'none';
                if (btnStage) {
                    btnStage.innerHTML = '◀';
                    btnStage.title = 'Ocultar Editor de Código';
                }
                const targetW = savedSidebarWidthBeforeCollapse || 680;
                updateSidebarWidth(Math.max(500, targetW));
            }
            if (window.network) setTimeout(() => network.redraw(), 100);
        }

        // 8. Alterna visibilidade do Grafo (Recolher / Expandir)
        let isGraphCollapsed = false;
        let savedSidebarWidthBeforeGraphCollapse = null;

        function toggleGraphPanel(forceState) {
            const networkContainer = document.getElementById('network-container');
            const resizer = document.getElementById('resizer');
            const sidebarToggle = document.getElementById('sidebar-toggle');
            const sidebar = document.getElementById('sidebar');
            const btnToggleGraph = document.getElementById('btn-toggle-graph');
            const btnNavReopenGraph = document.getElementById('btn-nav-reopen-graph');

            if (typeof forceState === 'boolean') {
                isGraphCollapsed = forceState;
            } else {
                isGraphCollapsed = !isGraphCollapsed;
            }

            const btnReopenStage = document.getElementById('btn-reopen-graph-stage');
            if (isGraphCollapsed) {
                networkContainer.style.display = 'none';
                if (resizer) resizer.style.display = 'none';
                if (sidebarToggle) sidebarToggle.style.display = 'none';
                savedSidebarWidthBeforeGraphCollapse = sidebar.style.width || (sidebar.offsetWidth + 'px');
                sidebar.style.width = '100%';
                sidebar.style.minWidth = '100%';
                sidebar.style.maxWidth = '100%';
                if (btnNavReopenGraph) btnNavReopenGraph.style.display = 'inline-flex';
                if (btnReopenStage) btnReopenStage.style.display = 'inline-flex';
                if (btnToggleGraph) {
                    btnToggleGraph.title = 'Reabrir Grafo';
                    btnToggleGraph.style.background = '#272822';
                    btnToggleGraph.style.color = '#a6e22e';
                    btnToggleGraph.style.borderColor = '#a6e22e';
                }
            } else {
                networkContainer.style.display = 'block';
                if (resizer) resizer.style.display = 'block';
                if (sidebarToggle) sidebarToggle.style.display = 'block';
                const prevW = savedSidebarWidthBeforeGraphCollapse || '600px';
                sidebar.style.width = prevW;
                sidebar.style.minWidth = '380px';
                sidebar.style.maxWidth = '90vw';
                if (btnNavReopenGraph) btnNavReopenGraph.style.display = 'none';
                if (btnReopenStage) btnReopenStage.style.display = 'none';
                if (btnToggleGraph) {
                    btnToggleGraph.title = 'Ocultar Grafo';
                    btnToggleGraph.style.background = '';
                    btnToggleGraph.style.color = '#66d9ef';
                    btnToggleGraph.style.borderColor = '';
                }
                if (window.network) {
                    setTimeout(() => {
                        network.redraw();
                    }, 100);
                }
            }
        }

        // Função de recolhimento progressivo em 2 estágios (1º Código • 2º Árvore)
        function handleStageCollapse() {
            const editor = document.getElementById('editor-subpanel');
            const isEditorOpen = editor && editor.style.display !== 'none';
            if (isEditorOpen) {
                toggleCodeSubpanel(true);
            } else {
                toggleSidebar();
            }
        }

        // Alterna visibilidade da barra lateral inteira
        function toggleSidebar() {
            const sb = document.getElementById('sidebar');
            const btnReopen = document.getElementById('sidebar-reopen-btn');
            const graphToolbar = document.getElementById('graph-toolbar');
            sb.classList.toggle('collapsed');
            const isCollapsed = sb.classList.contains('collapsed');
            if (btnReopen) btnReopen.style.display = isCollapsed ? 'inline-flex' : 'none';
            if (graphToolbar) graphToolbar.style.left = isCollapsed ? '52px' : '16px';
            if (window.network) setTimeout(() => network.redraw(), 260);
        }

        function updateSidebarWidth(newWidth) {
            const sidebar = document.getElementById('sidebar');
            sidebar.style.width = newWidth + 'px';
            sidebar.style.minWidth = newWidth + 'px';
            if (window.network) network.redraw();
            try {
                localStorage.setItem('graf_lens_sidebar_width', newWidth);
            } catch (e) {}
        }

        // 7. Redimensionamento do Resizer Externo (Sidebar vs Grafo)
        const resizer = document.getElementById('resizer');
        const sidebar = document.getElementById('sidebar');
        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            resizer.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const minW = isCodeCollapsed ? 200 : 380;
            const newWidth = Math.max(minW, Math.min(window.innerWidth - 200, e.clientX));
            updateSidebarWidth(newWidth);
        });

        window.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                if (window.network) network.redraw();
            }
        });

        // 8. Redimensionamento do Resizer Interno (Árvore vs Código)
        const internalResizer = document.getElementById('internal-resizer');
        const navSubpanel = document.getElementById('nav-subpanel');
        let isInternalResizing = false;

        internalResizer.addEventListener('mousedown', (e) => {
            isInternalResizing = true;
            internalResizer.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isInternalResizing) return;
            const sidebarRect = sidebar.getBoundingClientRect();
            const relX = e.clientX - sidebarRect.left;
            const newNavWidth = Math.max(180, Math.min(sidebarRect.width - 240, relX));
            navSubpanel.style.width = newNavWidth + 'px';
            navSubpanel.style.minWidth = newNavWidth + 'px';
        });

        window.addEventListener('mouseup', () => {
            if (isInternalResizing) {
                isInternalResizing = false;
                internalResizer.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                try {
                    const w = parseInt(navSubpanel.style.width, 10);
                    if (w) localStorage.setItem('graf_lens_nav_width', w);
                } catch (e) {}
            }
        });

        // Restauração das larguras personalizadas do usuário salvas no localStorage
        try {
            const savedSidebarWidth = localStorage.getItem('graf_lens_sidebar_width');
            if (savedSidebarWidth) {
                updateSidebarWidth(parseInt(savedSidebarWidth, 10));
            }
            const savedNavWidth = localStorage.getItem('graf_lens_nav_width');
            if (savedNavWidth && navSubpanel) {
                navSubpanel.style.width = savedNavWidth + 'px';
                navSubpanel.style.minWidth = savedNavWidth + 'px';
            }
        } catch (e) {}

        function copyCurrentCode() {
            if (!Mediator.currentNode || !rawFileSources[Mediator.currentNode.file]) return;
            const code = rawFileSources[Mediator.currentNode.file];
            navigator.clipboard.writeText(code).then(() => {
                showToast('📋 Código copiado com sucesso!');
            });
        }

        let cmEditorInstance = null;

        function getCodeMirrorMode(filePath) {
            if (!filePath) return 'null';
            const lower = filePath.toLowerCase();
            if (lower.endsWith('.php') || lower.endsWith('.blade.php')) return 'application/x-httpd-php';
            if (lower.endsWith('.py')) return 'python';
            if (lower.endsWith('.js') || lower.endsWith('.jsx')) return 'javascript';
            if (lower.endsWith('.ts') || lower.endsWith('.tsx')) return 'text/typescript';
            if (lower.endsWith('.html')) return 'htmlmixed';
            if (lower.endsWith('.css') || lower.endsWith('.scss')) return 'css';
            if (lower.endsWith('.json')) return 'application/json';
            if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'yaml';
            if (lower.endsWith('.sh') || lower.endsWith('.bash') || lower.endsWith('.zsh')) return 'shell';
            if (lower.endsWith('.md')) return 'markdown';
            if (lower.endsWith('.xml') || lower.endsWith('.svg')) return 'xml';
            return 'null';
        }

        function toggleEditMode(forceState) {
            if (!currentLoadedFilePath) {
                showToast('⚠️ Selecione um arquivo na árvore lateral antes de editar.', 'error');
                return;
            }
            if (typeof forceState === 'boolean') {
                isEditMode = forceState;
            } else {
                isEditMode = !isEditMode;
            }

            const tableContainer = document.getElementById('sublime-table-container');
            const textarea = document.getElementById('sublime-editor-textarea');
            const btnEdit = document.getElementById('btn-toggle-edit');
            const btnSave = document.getElementById('btn-save-code');
            const statusLang = document.getElementById('sublime-status-lang');

            if (isEditMode) {
                if (currentLoadedFilePath) {
                    pinEditorTab(currentLoadedFilePath);
                }
                tableContainer.style.display = 'none';
                const source = rawFileSources[currentLoadedFilePath] || '';

                if (window.CodeMirror) {
                    textarea.style.display = 'none';
                    if (!cmEditorInstance) {
                        cmEditorInstance = CodeMirror.fromTextArea(textarea, {
                            mode: getCodeMirrorMode(currentLoadedFilePath),
                            theme: 'monokai',
                            lineNumbers: true,
                            lineWrapping: true,
                            tabSize: 4,
                            indentUnit: 4,
                            extraKeys: {
                                "Ctrl-S": function() { saveCurrentCode(); },
                                "Cmd-S": function() { saveCurrentCode(); }
                            }
                        });
                        cmEditorInstance.on('change', () => {
                            rawFileSources[currentLoadedFilePath] = cmEditorInstance.getValue();
                        });
                    }
                    cmEditorInstance.setOption('mode', getCodeMirrorMode(currentLoadedFilePath));
                    cmEditorInstance.setValue(source);
                    cmEditorInstance.getWrapperElement().style.display = 'block';
                    setTimeout(() => cmEditorInstance.refresh(), 30);
                    cmEditorInstance.focus();
                } else {
                    textarea.style.display = 'block';
                    textarea.value = source;
                    textarea.focus();
                }

                btnEdit.innerHTML = '👁️';
                btnEdit.title = 'Voltar para Modo Visualização';
                btnEdit.style.background = '#fd971f';
                btnEdit.style.color = '#000000';
                btnSave.style.display = 'inline-flex';
                statusLang.innerText = `${statusLang.innerText.split('(')[0].trim()} (Modo Edição • Ctrl+S para Salvar)`;
            } else {
                if (cmEditorInstance) {
                    cmEditorInstance.getWrapperElement().style.display = 'none';
                    rawFileSources[currentLoadedFilePath] = cmEditorInstance.getValue();
                }
                textarea.style.display = 'none';
                tableContainer.style.display = 'block';
                btnEdit.innerHTML = '✏️';
                btnEdit.title = 'Entrar em Modo Edição';
                btnEdit.style.background = '';
                btnEdit.style.color = '';
                btnSave.style.display = 'none';
                Mediator.loadCode(currentLoadedFilePath);
            }
        }

        async function saveCurrentCode() {
            if (!currentLoadedFilePath) return;
            const content = (cmEditorInstance && isEditMode) 
                ? cmEditorInstance.getValue() 
                : document.getElementById('sublime-editor-textarea').value;
            const btnSave = document.getElementById('btn-save-code');
            const originalText = btnSave.innerHTML;
            btnSave.innerHTML = '⏳ Salvando...';
            btnSave.disabled = true;

            await executeBackendApi('/api/save-file', {
                path: currentLoadedFilePath,
                content: content
            }, '💾 Arquivo salvo com sucesso no disco!');

            btnSave.innerHTML = originalText;
            btnSave.disabled = false;
            rawFileSources[currentLoadedFilePath] = content;
        }

        // Atalhos de teclado: Tab (4 espaços) e Ctrl+S / Cmd+S para salvar instantaneamente
        document.addEventListener('DOMContentLoaded', () => {
            const editorTextarea = document.getElementById('sublime-editor-textarea');
            if (editorTextarea) {
                editorTextarea.addEventListener('keydown', (e) => {
                    if (e.key === 'Tab') {
                        e.preventDefault();
                        const start = editorTextarea.selectionStart;
                        const end = editorTextarea.selectionEnd;
                        editorTextarea.value = editorTextarea.value.substring(0, start) + '    ' + editorTextarea.value.substring(end);
                        editorTextarea.selectionStart = editorTextarea.selectionEnd = start + 4;
                    } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                        e.preventDefault();
                        saveCurrentCode();
                    }
                });
            }

            window.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                    if (isEditMode) {
                        e.preventDefault();
                        saveCurrentCode();
                    }
                }
            });
        });

        // 9. Busca em tempo real
        function onSearchInput(query) {
            query = (query || '').toLowerCase().trim();

            if (!query) {
                nodes.forEach(n => nodes.update({ id: n.id, hidden: false }));
            } else {
                nodes.forEach(n => {
                    const match = n.label.toLowerCase().includes(query) || n.id.toLowerCase().includes(query);
                    nodes.update({ id: n.id, hidden: !match });
                });
            }

            document.querySelectorAll('.tree-file-name, .tree-symbol-row').forEach(el => {
                const text = el.innerText.toLowerCase();
                const node = el.closest('.tree-node') || el;
                if (!query || text.includes(query)) {
                    node.style.display = '';
                    if (query && text.includes(query)) {
                        let p = node.parentElement;
                        while (p && p.classList.contains('tree-children')) {
                            p.classList.add('open');
                            const arrow = p.previousElementSibling?.querySelector('.tree-arrow');
                            if (arrow) arrow.classList.add('open');
                            p = p.parentElement.closest('.tree-children');
                        }
                    }
                } else {
                    if (el.classList.contains('tree-file-name')) {
                        node.style.display = 'none';
                    }
                }
            });
        }

        // 10. Controle do Modo Ao Vivo e Encerramento Gracioso
        let isLiveWatchActive = true;
        let evtSource = null;

        function toggleLiveWatch() {
            isLiveWatchActive = !isLiveWatchActive;
            const dot = document.getElementById('live-status-dot');
            const text = document.getElementById('live-status-text');
            const btnToggle = document.getElementById('btn-toggle-live');

            if (isLiveWatchActive) {
                if (dot) { dot.style.background = '#a6e22e'; dot.style.boxShadow = '0 0 5px #a6e22e'; }
                if (text) { text.style.color = '#a6e22e'; text.innerText = 'Ao Vivo'; }
                if (btnToggle) btnToggle.title = 'Clique para pausar a sincronização em tempo real';
                connectSSE();
                fetchLiveUpdate();
                showToast('▶ Monitoramento Ao Vivo ativado');
            } else {
                if (dot) { dot.style.background = '#75715e'; dot.style.boxShadow = 'none'; }
                if (text) { text.style.color = '#75715e'; text.innerText = 'Pausado'; }
                if (btnToggle) btnToggle.title = 'Clique para religar a sincronização em tempo real';
                if (evtSource) {
                    evtSource.close();
                    evtSource = null;
                }
                showToast('⏸️ Monitoramento Ao Vivo pausado');
            }
        }

        function shutdownServer() {
            if (!confirm("Deseja realmente desligar o servidor GrafLean? O processo Python será encerrado e a janela será fechada.")) return;
            fetch('/api/shutdown', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
                .finally(() => {
                    try {
                        window.open('', '_self', '');
                        window.close();
                    } catch (e) {}
                    showShutdownOverlay();
                });
        }

        function showShutdownOverlay() {
            const overlay = document.createElement('div');
            overlay.id = 'shutdown-overlay';
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.92);backdrop-filter:blur(10px);z-index:999999;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#f8f8f2;font-family:sans-serif;text-align:center;padding:20px;box-sizing:border-box;';
            overlay.innerHTML = `
                <div style="font-size:44px;margin-bottom:12px;">🛑</div>
                <h2 style="margin:0 0 8px 0;font-size:20px;color:#f8f8f2;font-weight:700;">Servidor GrafLean Encerrado</h2>
                <p style="color:#75715e;font-size:13px;margin:0 0 18px 0;max-width:380px;line-height:1.5;">O processo Python foi finalizado com sucesso. Você já pode fechar esta aba.</p>
                <button onclick="window.close()" class="sublime-btn" style="padding:6px 14px;background:#272822;color:#f8f8f2;border:1px solid #3e3d32;border-radius:6px;cursor:pointer;font-size:12px;">Fechar Aba</button>
            `;
            document.body.appendChild(overlay);
        }

        // 10. Sincronização em Tempo Real (Live Reload via SSE)
        function initLiveReload() {
            if (location.protocol.startsWith('http')) {
                const badge = document.createElement('div');
                badge.id = 'live-indicator';
                badge.style.cssText = 'position:fixed;bottom:10px;right:12px;background:rgba(14,14,14,0.75);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:2px 8px;font-size:10px;color:#75715e;font-family:sans-serif;display:inline-flex;align-items:center;gap:6px;box-shadow:0 2px 8px rgba(0,0,0,0.5);z-index:9999;';
                badge.innerHTML = `
                    <button id="btn-toggle-live" onclick="toggleLiveWatch()" style="background:transparent;border:none;color:inherit;font-size:10px;cursor:pointer;display:inline-flex;align-items:center;gap:4px;padding:2px 4px;border-radius:4px;transition:color 0.2s;" title="Clique para pausar a sincronização em tempo real">
                        <span id="live-status-dot" style="display:inline-block;width:5px;height:5px;background:#a6e22e;border-radius:50%;box-shadow:0 0 4px #a6e22e;"></span>
                        <span id="live-status-text" style="color:#a6e22e;font-weight:600;">Ao Vivo</span>
                    </button>
                    <span style="color:rgba(255,255,255,0.12);font-size:9px;">|</span>
                    <button id="btn-shutdown-server" onclick="shutdownServer()" style="background:transparent;border:none;color:#75715e;font-size:11px;cursor:pointer;display:inline-flex;align-items:center;padding:2px 4px;border-radius:4px;transition:color 0.2s;" title="Encerrar servidor GrafLean (finaliza processo Python e fecha janela)" onmouseover="this.style.color='#f92672'" onmouseout="this.style.color='#75715e'">⏻</button>
                `;
                document.body.appendChild(badge);

                const saved = sessionStorage.getItem('lens_session_state');
                if (saved) {
                    try {
                        const s = JSON.parse(saved);
                        sessionStorage.removeItem('lens_session_state');
                        if (s.nodeId) {
                            setTimeout(() => Mediator.select(s.nodeId, 'restore'), 100);
                        } else if (s.file) {
                            setTimeout(() => Mediator.loadCode(s.file, s.line || 1), 100);
                        }
                        if (s.navTab) switchNavTab(s.navTab);
                    } catch (e) {}
                }

                window.applyIncrementalPatch = function(eventType, payload) {
                    if (!payload) return;
                    if (eventType === 'node_created') {
                        const nodeId = payload.id || `file://${payload.path}`;
                        const fileName = payload.label || payload.path.split('/').pop();
                        const rawNode = {
                            id: nodeId,
                            label: fileName,
                            title: `🏷️ ${payload.path}\n🟢 Arquivo novo criado`,
                            type: payload.type || "file",
                            file: payload.path,
                            git: "new",
                            level: 1,
                            ca: 0,
                            ce: 0,
                            instability: 0,
                            deep: true,
                            cycle: false
                        };
                        allNodesMap.set(nodeId, rawNode);
                        if (nodes && !nodes.get(nodeId)) {
                            const formatted = formatVisNode(rawNode);
                            const finalSize = formatted.size || 15;
                            formatted.size = 2; // Inicia pequeno para efeito de scale-in
                            nodes.add(formatted);
                            setTimeout(() => {
                                if (nodes.get(nodeId)) {
                                    nodes.update({ id: nodeId, size: finalSize });
                                }
                            }, 50);
                        }
                        updateChangeSummaryStats();
                        showToast(`Novo arquivo detectado: ${rawNode.label}`, "info");
                    } else if (eventType === 'node_changed') {
                        const nodeId = payload.id || `file://${payload.path}`;
                        const raw = allNodesMap.get(nodeId);
                        if (raw) {
                            raw.git = "modified";
                            if (nodes && nodes.get(nodeId)) {
                                // Efeito de destaque luminoso âmbar temporário
                                nodes.update({
                                    id: nodeId,
                                    borderWidth: 4,
                                    color: { background: "#281c10", border: "#fd971f" }
                                });
                                setTimeout(() => {
                                    if (nodes.get(nodeId)) {
                                        nodes.update(formatVisNode(raw));
                                    }
                                }, 700);
                            }
                        }
                        updateChangeSummaryStats();
                    } else if (eventType === 'node_deleted') {
                        const nodeId = payload.id || `file://${payload.path}`;
                        const fileName = payload.path ? payload.path.split('/').pop() : 'arquivo';
                        allNodesMap.delete(nodeId);
                        if (nodes && nodes.get(nodeId)) {
                            // Dissolução suave: encolhe e fica vermelho antes de remover
                            nodes.update({
                                id: nodeId,
                                color: { background: "#281014", border: "#f92672" },
                                size: 3
                            });
                            setTimeout(() => {
                                if (nodes.get(nodeId)) {
                                    nodes.remove(nodeId);
                                }
                                updateChangeSummaryStats();
                            }, 350);
                        } else {
                            updateChangeSummaryStats();
                        }

                        showToast(`Arquivo excluído: ${fileName}`, "info");
                    } else if (eventType === 'edge_added') {
                        const edgeId = `${payload.source}->${payload.target}`;
                        if (edges && !edges.get(edgeId)) {
                            edges.add({
                                id: edgeId,
                                from: payload.source,
                                to: payload.target,
                                arrows: "to",
                                color: { color: "rgba(255,255,255,0.18)", highlight: "#66d9ef" },
                                width: 1.2
                            });
                        }
                    } else if (eventType === 'edge_removed') {
                        const edgeId = `${payload.source}->${payload.target}`;
                        if (edges && edges.get(edgeId)) {
                            edges.remove(edgeId);
                        }
                    } else if (eventType === 'ai_state') {
                        aiTaskStates[payload.path] = payload.state;
                        const fileName = payload.path ? payload.path.split('/').pop() : 'arquivo';

                        // Atualiza indicador da toolbar
                        const aiIndicator = document.getElementById('ai-active-indicator');
                        if (aiIndicator) {
                            if (payload.state === 'creating' || payload.state === 'editing' || payload.state === 'analyzing') {
                                aiIndicator.style.display = 'inline-block';
                                aiIndicator.innerText = `⚡ IA: ${payload.state.toUpperCase()} (${fileName})`;
                            } else if (payload.state === 'idle' || payload.state === 'finished') {
                                aiIndicator.style.display = 'none';
                            }
                        }

                        // Atualiza a cápsula no topo (AI Status Capsule)
                        const capsule = document.getElementById('ai-status-capsule');
                        const capsuleText = document.getElementById('ai-capsule-text');
                        if (capsule) {
                            if (payload.state === 'creating' || payload.state === 'editing' || payload.state === 'analyzing') {
                                capsule.style.display = 'inline-flex';
                                if (capsuleText) capsuleText.innerText = `⚡ ${payload.state.toUpperCase()}: ${fileName}`;
                            } else if (payload.state === 'idle' || payload.state === 'finished') {
                                if (capsuleText) capsuleText.innerText = `✅ IA: Concluído`;
                                setTimeout(() => {
                                    if (capsule && (!payload.state || payload.state === 'idle' || payload.state === 'finished')) {
                                        capsule.style.display = 'none';
                                    }
                                }, 3000);
                            }
                        }

                        const nodeId = `file://${payload.path}`;
                        const raw = allNodesMap.get(nodeId);
                        if (raw && nodes && nodes.get(nodeId)) {
                            nodes.update(formatVisNode(raw));
                        }
                        updateChangeSummaryStats();
                    } else if (eventType === 'git_status') {
                        const targetPath = payload.path;
                        allNodesMap.forEach(n => {
                            if (!targetPath || targetPath === 'all' || n.file === targetPath || n.id === targetPath || n.id === `file://${targetPath}`) {
                                if (payload.status === 'committed') {
                                    n.git = '';
                                } else {
                                    n.git = payload.status;
                                }
                                if (nodes && nodes.get(n.id)) {
                                    nodes.update(formatVisNode(n));
                                }
                            }
                        });
                        updateChangeSummaryStats();
                    }
                };

                window.connectSSE = function() {
                    if (evtSource) return;
                    evtSource = new EventSource('/events');

                    // Eventos Semânticos Incrementais (Fase A / B / E)
                    const semanticEvents = ['node_created', 'node_changed', 'node_deleted', 'edge_added', 'edge_removed', 'ai_state', 'git_status'];
                    semanticEvents.forEach(evtName => {
                        evtSource.addEventListener(evtName, (e) => {
                            try {
                                const data = JSON.parse(e.data);
                                applyIncrementalPatch(evtName, data);
                            } catch (err) {
                                console.error('Erro ao processar patch SSE:', err);
                            }
                        });
                    });

                    // Fallback para reload completo
                    evtSource.addEventListener('update', () => {
                        if (isLiveWatchActive) fetchLiveUpdate();
                    });
                    evtSource.addEventListener('reload', () => {
                        if (isLiveWatchActive) fetchLiveUpdate();
                    });
                    evtSource.onerror = () => {
                        if (!isLiveWatchActive) return;
                        const dot = document.getElementById('live-status-dot');
                        const text = document.getElementById('live-status-text');
                        if (dot) { dot.style.background = '#fd971f'; dot.style.boxShadow = 'none'; }
                        if (text) { text.style.color = '#fd971f'; text.innerText = 'Reconectando...'; }
                    };
                    evtSource.onopen = () => {
                        if (!isLiveWatchActive) return;
                        const dot = document.getElementById('live-status-dot');
                        const text = document.getElementById('live-status-text');
                        if (dot) { dot.style.background = '#a6e22e'; dot.style.boxShadow = '0 0 4px #a6e22e'; }
                        if (text) { text.style.color = '#a6e22e'; text.innerText = 'Ao Vivo'; }
                    };
                };
                connectSSE();

                // Telemetria leve de FPS (Fase F.5)
                let frameCount = 0;
                let lastFpsTime = performance.now();
                function fpsLoop(now) {
                    frameCount++;
                    if (now - lastFpsTime >= 1000) {
                        const fps = Math.round((frameCount * 1000) / (now - lastFpsTime));
                        const fpsEl = document.getElementById('telemetry-fps');
                        if (fpsEl) fpsEl.innerText = `${fps} FPS`;
                        frameCount = 0;
                        lastFpsTime = now;
                    }
                    requestAnimationFrame(fpsLoop);
                }
                requestAnimationFrame(fpsLoop);
            }
        }
        initLiveReload();

        // 11. Menu de Contexto da Árvore (Criar Pasta/MD, Renomear, Excluir)
        let activeContextType = null;
        let activeContextPath = null;
        let activeContextName = null;

        function openTreeContextMenu(e, type, relPath, name) {
            activeContextType = type;
            activeContextPath = relPath || '';
            activeContextName = name;

            const menu = document.getElementById('tree-context-menu');
            menu.innerHTML = '';

            const header = document.createElement('div');
            header.className = 'tree-context-header';
            header.innerText = (type === 'directory' ? '📁 ' : '📄 ') + name;
            menu.appendChild(header);

            if (type === 'directory') {
                const btnNewFolder = document.createElement('button');
                btnNewFolder.className = 'tree-context-item';
                btnNewFolder.innerHTML = '<span>📁</span> Criar pasta';
                btnNewFolder.onclick = () => promptCreateFolder(activeContextPath);
                menu.appendChild(btnNewFolder);

                const btnNewFile = document.createElement('button');
                btnNewFile.className = 'tree-context-item';
                btnNewFile.innerHTML = '<span>📄</span> Criar arquivo';
                btnNewFile.onclick = () => promptCreateFile(activeContextPath);
                menu.appendChild(btnNewFile);

                const btnRename = document.createElement('button');
                btnRename.className = 'tree-context-item';
                btnRename.innerHTML = '<span>✏️</span> Renomear pasta';
                btnRename.onclick = () => promptRename(activeContextPath, activeContextName);
                menu.appendChild(btnRename);

                const btnDelete = document.createElement('button');
                btnDelete.className = 'tree-context-item danger';
                btnDelete.innerHTML = '<span>🗑️</span> Excluir pasta';
                btnDelete.onclick = () => promptDelete(activeContextPath, activeContextName, true);
                menu.appendChild(btnDelete);
            } else {
                const btnRename = document.createElement('button');
                btnRename.className = 'tree-context-item';
                btnRename.innerHTML = '<span>✏️</span> Renomear arquivo';
                btnRename.onclick = () => promptRename(activeContextPath, activeContextName);
                menu.appendChild(btnRename);

                const btnDelete = document.createElement('button');
                btnDelete.className = 'tree-context-item danger';
                btnDelete.innerHTML = '<span>🗑️</span> Excluir arquivo';
                btnDelete.onclick = () => promptDelete(activeContextPath, activeContextName, false);
                menu.appendChild(btnDelete);
            }

            const posX = Math.min(e.clientX + 10, window.innerWidth - 190);
            const posY = Math.min(e.clientY + 5, window.innerHeight - 200);
            menu.style.left = posX + 'px';
            menu.style.top = posY + 'px';
            menu.style.display = 'flex';
        }

        function closeTreeContextMenu() {
            const menu = document.getElementById('tree-context-menu');
            if (menu) menu.style.display = 'none';
        }

        document.addEventListener('click', (e) => {
            if (!e.target.closest('#tree-context-menu')) {
                closeTreeContextMenu();
            }
        });

        async function executeBackendApi(endpoint, payload, actionSuccessMsg) {
            const baseUrl = location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:7357';
            try {
                const res = await fetch(baseUrl + endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast(actionSuccessMsg);
                    if (data.data) {
                        applyLiveUpdate(data.data);
                    } else {
                        fetchLiveUpdate();
                    }
                } else {
                    showToast('❌ Erro: ' + (data.error || 'Operação falhou'), 'error');
                }
            } catch (err) {
                showToast('⚠️ O servidor HTTP local do GrafLean não está respondendo.', 'error');
            }
        }

        async function promptCreateFolder(parentRelPath) {
            closeTreeContextMenu();
            const targetDesc = parentRelPath || 'raiz do projeto';
            const folderName = window.prompt(`Criar nova pasta dentro de "${targetDesc}":`);
            if (!folderName || !folderName.trim()) return;

            const finalRelPath = parentRelPath ? `${parentRelPath}/${folderName.trim()}` : folderName.trim();
            await executeBackendApi('/api/create-folder', { path: finalRelPath }, `✅ Pasta "${folderName.trim()}" criada com sucesso!`);
        }

        async function promptCreateFile(parentRelPath) {
            closeTreeContextMenu();
            const targetDesc = parentRelPath || 'raiz do projeto';
            let fileName = window.prompt(`Criar arquivo em "${targetDesc}":`, 'novo_arquivo.md');
            if (!fileName || !fileName.trim()) return;

            const finalRelPath = parentRelPath ? `${parentRelPath}/${fileName.trim()}` : fileName.trim();
            if (parentRelPath) {
                openFolders.add(parentRelPath);
                try {
                    localStorage.setItem('graf_lens_open_folders', JSON.stringify(Array.from(openFolders)));
                } catch (e) {}
            }
            await executeBackendApi('/api/create-file', { path: finalRelPath, content: '' }, `✅ Arquivo "${fileName.trim()}" criado com sucesso!`);
        }

        async function promptRename(relPath, currentName) {
            closeTreeContextMenu();
            const newName = window.prompt(`Renomear "${currentName}" para:`, currentName);
            if (!newName || !newName.trim() || newName.trim() === currentName) return;

            await executeBackendApi('/api/rename', { old_path: relPath, new_name: newName.trim() }, `✅ Renomeado para "${newName.trim()}"!`);
        }

        async function promptDelete(relPath, currentName, isDir) {
            closeTreeContextMenu();
            const confirmMsg = `⚠️ ATENÇÃO: Deseja realmente excluir permanentemente ${isDir ? 'a pasta' : 'o arquivo'} "${currentName}"?\n\nEsta ação não poderá ser desfeita.`;
            if (!window.confirm(confirmMsg)) return;

            await executeBackendApi('/api/delete', { path: relPath }, `🗑️ "${currentName}" foi excluído com sucesso!`);
        }

        // ==========================================
        // Quick Palette (Busca Rápida Estilo Ctrl+P)
        // ==========================================
        let quickPaletteActiveIndex = 0;
        let quickPaletteFilteredItems = [];

        function getAllIndexableItems() {
            const items = [];
            function traverse(node) {
                if (!node) return;
                if (node.type === 'file' || node.type === 'code' || node.type === 'doc') {
                    items.push({
                        name: node.name,
                        path: node.path,
                        isSymbol: false,
                        icon: typeof getFileIcon === 'function' ? getFileIcon(node.name) : '📄'
                    });
                }
                if (node.children) {
                    node.children.forEach(traverse);
                }
            }
            if (typeof rawTree !== 'undefined' && rawTree) traverse(rawTree);

            // Indexa símbolos do grafo (classes e funções)
            if (typeof rawNodes !== 'undefined' && Array.isArray(rawNodes)) {
                rawNodes.forEach(n => {
                    if (n.type === 'class' || n.type === 'function' || n.type === 'method') {
                        items.push({
                            name: n.label,
                            path: n.parentId || n.id,
                            symbolId: n.id,
                            isSymbol: true,
                            symbolType: n.type,
                            icon: n.type === 'class' ? '🔷' : '⚡'
                        });
                    }
                });
            }
            return items;
        }

        function openQuickPalette() {
            const backdrop = document.getElementById('quick-palette-backdrop');
            const input = document.getElementById('quick-palette-input');
            if (!backdrop || !input) return;
            backdrop.style.display = 'flex';
            input.value = '';
            input.focus();
            onQuickPaletteInput('');
        }

        function closeQuickPalette() {
            const backdrop = document.getElementById('quick-palette-backdrop');
            if (backdrop) backdrop.style.display = 'none';
        }

        function onQuickPaletteInput(query) {
            const q = query.trim().toLowerCase();
            const allItems = getAllIndexableItems();
            if (!q) {
                quickPaletteFilteredItems = allItems.slice(0, 30);
            } else {
                quickPaletteFilteredItems = allItems.filter(item => {
                    return item.name.toLowerCase().includes(q) || item.path.toLowerCase().includes(q);
                }).slice(0, 40);
            }
            quickPaletteActiveIndex = 0;
            renderQuickPalette();
        }

        function renderQuickPalette() {
            const container = document.getElementById('quick-palette-results');
            if (!container) return;
            if (quickPaletteFilteredItems.length === 0) {
                container.innerHTML = '<div style="padding:16px; text-align:center; color:#75715e; font-size:12px;">Nenhum arquivo ou símbolo encontrado</div>';
                return;
            }
            container.innerHTML = quickPaletteFilteredItems.map((item, idx) => `
                <div class="quick-palette-item ${idx === quickPaletteActiveIndex ? 'active' : ''}" onclick="selectQuickPaletteItem(${idx})">
                    <div style="display:flex; align-items:center; gap:8px; overflow:hidden;">
                        <span>${item.icon}</span>
                        <span style="font-weight:600; color:${item.isSymbol ? '#66d9ef' : '#f8f8f2'};">${item.name}</span>
                        <span style="color:#75715e; font-size:11px; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;">${item.path}</span>
                    </div>
                    <span style="font-size:10px; color:#75715e; background:#181818; padding:2px 6px; border-radius:4px; border:1px solid #282828;">${item.isSymbol ? item.symbolType : 'arquivo'}</span>
                </div>
            `).join('');
            const activeEl = container.children[quickPaletteActiveIndex];
            if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
        }

        function onQuickPaletteKeyDown(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (quickPaletteActiveIndex < quickPaletteFilteredItems.length - 1) {
                    quickPaletteActiveIndex++;
                    renderQuickPalette();
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (quickPaletteActiveIndex > 0) {
                    quickPaletteActiveIndex--;
                    renderQuickPalette();
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                selectQuickPaletteItem(quickPaletteActiveIndex);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeQuickPalette();
            }
        }

        function selectQuickPaletteItem(idx) {
            const item = quickPaletteFilteredItems[idx];
            if (!item) return;
            closeQuickPalette();
            if (item.isSymbol) {
                if (item.path && typeof rawFileSources !== 'undefined' && rawFileSources[item.path]) openFile(item.path);
                if (item.symbolId && typeof focusNode === 'function') focusNode(item.symbolId);
            } else {
                openFile(item.path);
            }
        }

        // ==========================================
        // Find in Files (Busca Global de Conteúdo)
        // ==========================================
        let findFilesResults = [];
        let findFilesActiveIndex = 0;
        let findFilesCaseSensitive = false;
        let findFilesDebounceTimer = null;

        function openFindInFiles() {
            const backdrop = document.getElementById('find-files-backdrop');
            const input = document.getElementById('find-files-input');
            if (!backdrop || !input) return;
            backdrop.style.display = 'flex';
            input.focus();
            input.select();
            if (input.value.trim()) {
                executeFindInFiles(input.value);
            }
        }

        function closeFindInFiles() {
            const backdrop = document.getElementById('find-files-backdrop');
            if (backdrop) backdrop.style.display = 'none';
        }

        function toggleFindCaseSensitive() {
            findFilesCaseSensitive = !findFilesCaseSensitive;
            const btn = document.getElementById('btn-find-case');
            if (btn) btn.classList.toggle('active', findFilesCaseSensitive);
            const input = document.getElementById('find-files-input');
            if (input && input.value.trim()) executeFindInFiles(input.value);
        }

        function onFindInFilesInput(query) {
            clearTimeout(findFilesDebounceTimer);
            findFilesDebounceTimer = setTimeout(() => {
                executeFindInFiles(query);
            }, 180);
        }

        async function executeFindInFiles(query) {
            const q = (query || '').trim();
            const resultsContainer = document.getElementById('find-files-results');
            const countLabel = document.getElementById('find-files-count');
            if (!q) {
                findFilesResults = [];
                if (resultsContainer) resultsContainer.innerHTML = '<div style="padding:20px; text-align:center; color:#75715e;">Digite um termo para pesquisar em todos os arquivos...</div>';
                if (countLabel) countLabel.innerText = '';
                return;
            }

            if (resultsContainer) resultsContainer.innerHTML = '<div style="padding:20px; text-align:center; color:#66d9ef;">⚡ Pesquisando nos arquivos do projeto...</div>';

            try {
                const res = await fetch('/api/search-content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: q, case_sensitive: findFilesCaseSensitive, max_results: 100 })
                });
                const json = await res.json();
                if (json.success && Array.isArray(json.results)) {
                    findFilesResults = json.results;
                    findFilesActiveIndex = 0;
                    renderFindInFilesResults(q);
                } else {
                    if (resultsContainer) resultsContainer.innerHTML = '<div style="padding:20px; text-align:center; color:#f92672;">Erro ao executar pesquisa.</div>';
                }
            } catch (err) {
                if (resultsContainer) resultsContainer.innerHTML = '<div style="padding:20px; text-align:center; color:#fd971f;">Servidor local indisponível.</div>';
            }
        }

        function highlightMatchText(text, query) {
            if (!query) return escapeHtml(text);
            const escapedText = escapeHtml(text);
            const escapedQuery = escapeHtml(query);
            const flags = findFilesCaseSensitive ? 'g' : 'gi';
            const regex = new RegExp(`(${escapedQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, flags);
            return escapedText.replace(regex, '<span class="find-highlight">$1</span>');
        }

        function renderFindInFilesResults(query) {
            const container = document.getElementById('find-files-results');
            const countLabel = document.getElementById('find-files-count');
            if (!container) return;

            if (findFilesResults.length === 0) {
                container.innerHTML = '<div style="padding:20px; text-align:center; color:#75715e;">Nenhum resultado encontrado para "' + escapeHtml(query) + '"</div>';
                if (countLabel) countLabel.innerText = '0 ocorrências';
                return;
            }

            if (countLabel) countLabel.innerText = `${findFilesResults.length} ocorrências`;

            // Agrupa por arquivo
            const grouped = new Map();
            findFilesResults.forEach((r, idx) => {
                if (!grouped.has(r.file)) grouped.set(r.file, []);
                grouped.get(r.file).push({ ...r, globalIndex: idx });
            });

            let html = '';
            grouped.forEach((items, filePath) => {
                const fileName = filePath.split('/').pop();
                const iconInfo = typeof getFileIcon === 'function' ? getFileIcon(fileName) : { icon: '📄' };
                html += `
                    <div class="find-file-group">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span>${iconInfo.icon}</span>
                            <span>${filePath}</span>
                        </div>
                        <span style="font-size:10px; color:#75715e; font-weight:normal;">${items.length} matches</span>
                    </div>
                `;
                items.forEach(item => {
                    const isActive = item.globalIndex === findFilesActiveIndex;
                    html += `
                        <div class="find-result-item ${isActive ? 'active' : ''}" onclick="selectFindInFilesItem(${item.globalIndex})">
                            <span class="find-line-num">L${item.line}</span>
                            <span class="find-snippet">${highlightMatchText(item.snippet, query)}</span>
                        </div>
                    `;
                });
            });

            container.innerHTML = html;
            const activeEl = container.querySelector('.find-result-item.active');
            if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
        }

        function onFindInFilesKeyDown(e) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (findFilesActiveIndex < findFilesResults.length - 1) {
                    findFilesActiveIndex++;
                    renderFindInFilesResults(document.getElementById('find-files-input').value);
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (findFilesActiveIndex > 0) {
                    findFilesActiveIndex--;
                    renderFindInFilesResults(document.getElementById('find-files-input').value);
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                selectFindInFilesItem(findFilesActiveIndex);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeFindInFiles();
            }
        }

        function selectFindInFilesItem(idx) {
            const item = findFilesResults[idx];
            if (!item) return;
            closeFindInFiles();
            Mediator.loadCode(item.file, item.line);
        }

        window.addEventListener('keydown', (e) => {
            const activeTag = (document.activeElement && document.activeElement.tagName) ? document.activeElement.tagName.toLowerCase() : '';
            const isInputFocused = activeTag === 'input' || activeTag === 'textarea' || (document.activeElement && document.activeElement.classList.contains('CodeMirror-code'));

            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'f') {
                e.preventDefault();
                openFindInFiles();
            } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'p') {
                e.preventDefault();
                openQuickPalette();
            } else if (e.key === 'Escape') {
                closeQuickPalette();
                closeFindInFiles();
            } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'w') {
                if (currentLoadedFilePath) {
                    e.preventDefault();
                    closeEditorTab(currentLoadedFilePath);
                }
            } else if (e.ctrlKey && e.key === 'Tab') {
                e.preventDefault();
                cycleNextTab(e.shiftKey ? -1 : 1);
            } else if (e.altKey && (e.key.toLowerCase() === 'n' || e.key === 'ArrowRight')) {
                e.preventDefault();
                focusNextChange();
            } else if (e.altKey && (e.key.toLowerCase() === 'p' || e.key === 'ArrowLeft')) {
                e.preventDefault();
                focusPreviousChange();
            } else if (!isInputFocused && !e.ctrlKey && !e.metaKey && !e.altKey) {
                if (e.key === '1') {
                    switchPerspective('code');
                } else if (e.key === '2') {
                    switchPerspective('change');
                }
            }
        });
    