#!/usr/bin/env python3
"""
CLI Unificada — GrafLean (Architecture & Agent Orchestration Lens).
Permite escanear projetos, gerar mapas visuais, auditar métricas, inspecionar símbolos
e criar recursos (pastas e especificações Markdown) para orquestração de agentes.
"""

import sys
import os
import webbrowser

# Garante que o diretório do projeto esteja no sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.graph import ProjectGraph
from core.visualizer import ArchitectureVisualizer


def print_help():
    print("""
🏛️ GrafLean — Architecture & Agent Orchestration CLI

Uso:
  python3 lens.py                                      # Inicia o Hub Central e abre no navegador (localhost:7357)
  python3 lens.py hub [--port PORTA] [--no-browser]    # Inicia o servidor do Hub Central
  python3 lens.py add <diretorio> [--name NOME] [--no-ai] # Registra projeto na biblioteca central
  python3 lens.py list                                 # Lista os projetos cadastrados na biblioteca
  python3 lens.py rm <id_do_projeto>                   # Remove um projeto da biblioteca
  python3 lens.py scan [diretorio]                     # Escaneia o projeto e gera .arch_graph.json
  python3 lens.py map [diretorio]                      # Gera o mapa interativo arch_map.html e abre no navegador
  python3 lens.py watch [diretorio]                    # Modo vigilante: Live-reload e API ativa em tempo real
  python3 lens.py audit [diretorio]                    # Audita ciclos de dependência e estabilidade arquitetural
  python3 lens.py info [simbolo] [dir]                 # Exibe diagnóstico arquitetural de uma classe/método
  python3 lens.py new folder <caminho>                 # Cria pasta com segurança contra path traversal
  python3 lens.py new md <caminho> [--template NOME]   # Cria especificação MD (task, spec, context, empty)
  python3 lens.py rename <antigo> <novo_nome>          # Renomeia arquivo ou pasta com segurança
  python3 lens.py delete <caminho>                     # Exclui arquivo ou pasta com segurança
    """)


def main():
    if len(sys.argv) < 2:
        print("🏛️ Iniciando GrafLean Hub (Workspace Centralizado & PWA)...")
        from core.hub_server import HubServer
        hub = HubServer(port=7357)
        hub.start(block=True, open_browser=True)
        return

    if sys.argv[1] in ("-h", "--help", "help"):
        print_help()
        return

    cmd = sys.argv[1]
    target_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else "."

    if cmd == "hub":
        port = 7357
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        open_browser = "--no-browser" not in sys.argv
        print(f"🏛️ GrafLean Hub ativo em: http://127.0.0.1:{port}")
        from core.hub_server import HubServer
        hub = HubServer(port=port)
        hub.start(block=True, open_browser=open_browser)

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Uso: python3 lens.py add <diretorio> [--name Nome] [--no-ai]")
            return
        proj_path = sys.argv[2]
        proj_name = None
        if "--name" in sys.argv:
            n_idx = sys.argv.index("--name")
            if n_idx + 1 < len(sys.argv):
                proj_name = sys.argv[n_idx + 1]
        ai_acc = "--no-ai" not in sys.argv
        from core.hub_server import HubManager
        manager = HubManager()
        try:
            meta = manager.register_and_index(proj_path, name=proj_name, ai_accelerator=ai_acc)
            print(f"✅ Projeto '{meta.name}' cadastrado com sucesso no Hub!")
            print(f"  • ID: {meta.id}")
            print(f"  • Caminho: {meta.path}")
            print(f"  • Modo: {'⚡ Acelerador de IA (.graflean/)' if meta.ai_accelerator else '🛡️ Zero-Footprint'}")
            print(f"  • Estatísticas: {meta.node_count} nós, {meta.edge_count} conexões.")
        except Exception as e:
            print(f"❌ Erro ao cadastrar projeto: {e}")

    elif cmd in ("list", "ls"):
        from core.library import LibraryManager
        lib = LibraryManager()
        projects = lib.list_projects()
        if not projects:
            print("📁 Nenhum projeto cadastrado na biblioteca. Use: python3 lens.py add <diretorio>")
            return
        print(f"\n🏛️ Projetos Cadastrados no GrafLean Hub ({len(projects)}):")
        print("-" * 75)
        for p in projects:
            mode = "⚡ IA Ativo" if p.ai_accelerator else "🛡️ Zero-Footprint"
            cycles = "⚠️ Ciclos" if p.has_cycles else "✅ Acíclico"
            print(f"• [{p.id}] {p.name}")
            print(f"  Caminho: {p.path}")
            print(f"  Modo: {mode} | Nós: {p.node_count} | Conexões: {p.edge_count} | I: {p.avg_instability} | {cycles}")
            print("-" * 75)

    elif cmd == "rm":
        if len(sys.argv) < 3:
            print("Uso: python3 lens.py rm <id_do_projeto>")
            return
        proj_id = sys.argv[2]
        from core.hub_server import HubManager
        manager = HubManager()
        if manager.remove_project(proj_id, purge_local_folder=True):
            print(f"🗑️ Projeto '{proj_id}' removido com sucesso da biblioteca!")
        else:
            print(f"❌ Projeto com ID '{proj_id}' não encontrado.")

    elif cmd == "scan":
        print(f"🔍 Escaneando arquitetura em: {os.path.abspath(target_dir)}")
        g = ProjectGraph(target_dir)
        g.scan_project()
        out_path = g.save_to_file()
        print(f"✅ Grafo salvo em: {out_path}")
        print(f"📊 Estatísticas: {len(g.nodes)} nós, {len(g.edges)} conexões mapeadas.")

    elif cmd == "map":
        print(f"🗺️ Gerando mapa arquitetural para: {os.path.abspath(target_dir)}")
        g = ProjectGraph(target_dir)
        g.scan_project()
        g.save_to_file()
        viz = ArchitectureVisualizer(g)
        html_path = viz.generate_html()
        print(f"✅ Mapa interativo gerado: {html_path}")

        if "--static" in sys.argv:
            print("📄 Modo estático ativado. Abrindo arquivo local...")
            webbrowser.open(f"file://{html_path}")
        else:
            port = 7357
            if "--port" in sys.argv:
                idx = sys.argv.index("--port")
                if idx + 1 < len(sys.argv):
                    port = int(sys.argv[idx + 1])
            from core.watcher import ArchitectureWatcher
            watcher = ArchitectureWatcher(target_dir, port=port)
            watcher.start_watching()

    elif cmd == "watch":
        port = 7357
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        from core.watcher import ArchitectureWatcher
        watcher = ArchitectureWatcher(target_dir, port=port)
        watcher.start_watching()

    elif cmd == "audit":
        print(f"⚖️ Auditando arquitetura em: {os.path.abspath(target_dir)}")
        g = ProjectGraph(target_dir)
        g.scan_project()
        cycles = g.analyzer.detect_cycles()
        if cycles:
            print(f"⚠️ ATENÇÃO: {len(cycles)} ciclo(s) de dependência detectado(s):")
            for c in cycles:
                print("  " + " ➔ ".join(c))
        else:
            print("✅ Parabéns! Zero ciclos de dependência detectados (A ➔ B ➔ A limpo).")

        # Top 5 classes mais estáveis e mais instáveis
        classes = [n for n in g.nodes.values() if n.symbol_type.value == "class"]
        if classes:
            print("\n🏛️ Módulos e Instabilidade (Clean Architecture):")
            classes_sorted = sorted(classes, key=lambda c: c.metrics.instability)
            for c in classes_sorted[:5]:
                print(f"  • {c.name}: I = {c.metrics.instability} (Ca={c.metrics.afferent_coupling}, Ce={c.metrics.efferent_coupling})")

    elif cmd == "info":
        if len(sys.argv) < 3:
            print("Uso: python3 lens.py info [NomeDoSimbolo] [diretorio_opcional]")
            return
        symbol_name = sys.argv[2]
        scan_dir = sys.argv[3] if len(sys.argv) > 3 else "."
        g = ProjectGraph(scan_dir)
        g.scan_project()
        node = g.find_symbol(symbol_name)
        if not node:
            print(f"❌ Símbolo '{symbol_name}' não encontrado no projeto.")
            return

        m = node.metrics
        print(f"\n🏷️  Símbolo: {node.name} ({node.symbol_type.value.upper()})")
        print(f"📁 Arquivo: {node.file_path}:{node.line}")
        if node.docstring:
            print(f"📖 Propósito: {node.docstring}")
        print(f"⚖️  Métricas: Ca={m.afferent_coupling} | Ce={m.efferent_coupling} | Instabilidade={m.instability}")

        inbound = g.analyzer.get_inbound_callers(node.id)
        if inbound:
            print("\n📥 Chamado por:")
            for caller in inbound:
                print(f"  • {caller}")

        outbound = g.analyzer.get_outbound_dependencies(node.id)
        if outbound:
            print("\n📤 Depende de:")
            for dep in outbound:
                print(f"  • {dep}")

    elif cmd == "new":
        if len(sys.argv) < 3 or sys.argv[2] in ("-h", "--help"):
            print("""
Uso do comando new:
  python3 lens.py new folder <caminho>
  python3 lens.py new md <caminho> [--template task|spec|context|empty]

Exemplos:
  python3 lens.py new folder docs/specs
  python3 lens.py new md docs/specs/TASK_AUTH.md --template task
            """)
            return

        sub_type = sys.argv[2].lower()
        if sub_type == "folder":
            if len(sys.argv) < 4:
                print("❌ Especifique o caminho da pasta: python3 lens.py new folder <caminho>")
                return
            folder_path = sys.argv[3]
            from core.creator import create_folder
            try:
                full_path = create_folder(".", folder_path)
                print(f"✅ Pasta criada com sucesso: {full_path}")
            except Exception as e:
                print(f"❌ Erro ao criar pasta: {e}")

        elif sub_type in ("md", "file"):
            if len(sys.argv) < 4:
                print("❌ Especifique o caminho do arquivo: python3 lens.py new md <caminho> [--template task|spec|context]")
                return
            file_path = sys.argv[3]
            template = "task"
            if "--template" in sys.argv:
                t_idx = sys.argv.index("--template")
                if t_idx + 1 < len(sys.argv):
                    template = sys.argv[t_idx + 1]
            from core.creator import create_markdown_spec
            try:
                full_path = create_markdown_spec(".", file_path, template_key=template)
                print(f"✅ Arquivo Markdown criado com sucesso ({template}): {full_path}")
            except Exception as e:
                print(f"❌ Erro ao criar arquivo Markdown: {e}")
        else:
            print(f"❌ Tipo desconhecido: '{sub_type}'. Use 'folder' ou 'md'.")

    elif cmd == "rename":
        if len(sys.argv) < 4:
            print("Uso: python3 lens.py rename <caminho_antigo> <novo_nome_ou_caminho>")
            return
        old_path = sys.argv[2]
        new_name = sys.argv[3]
        from core.creator import rename_resource
        try:
            full_path = rename_resource(".", old_path, new_name)
            print(f"✅ Renomeado com sucesso para: {full_path}")
        except Exception as e:
            print(f"❌ Erro ao renomear: {e}")

    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Uso: python3 lens.py delete <caminho_do_arquivo_ou_pasta>")
            return
        target_path = sys.argv[2]
        from core.creator import delete_resource
        try:
            full_path = delete_resource(".", target_path)
            print(f"🗑️ Excluído com sucesso: {full_path}")
        except Exception as e:
            print(f"❌ Erro ao excluir: {e}")

    else:
        print_help()


if __name__ == "__main__":
    main()
