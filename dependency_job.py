import pandas as pd
import networkx as nx
import streamlit as st
from streamlit_tree_select import tree_select
from pyvis.network import Network
import streamlit.components.v1 as components
import json
import sys
import os 
from fuzzywuzzy import process 

# Meningkatkan batas kedalaman rekursi untuk Graph yang besar
sys.setrecursionlimit(3000) 

# Set konfigurasi halaman
st.set_page_config(layout="wide", page_title="Job Hierarchy Viewer - MIS PROPERTY")

# --- 1. Load data ---
try:
    df = pd.read_excel("job_hirarki.xlsx") 
except FileNotFoundError:
    st.error("❌ Error: File 'job_hirarki.xlsx' tidak ditemukan. Pastikan file ada di direktori yang sama.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error saat memuat file Excel: {e}")
    st.stop()


# ====================================================================
# === 2. Graph creation and Utility Functions ===
# ====================================================================

df['JOB Name'] = df['JOB Name'].astype(str).str.strip()
df['Sequence'] = df['Sequence'].fillna('').astype(str).str.strip()

G = nx.DiGraph()
valid_jobs = set()

for job_name in df['JOB Name'].unique():
    if job_name and job_name.lower() not in ["nan", "not available", ""]:
        G.add_node(job_name)
        valid_jobs.add(job_name)
        
for _, row in df.iterrows():
    job = row['JOB Name']
    seq = row['Sequence']
    
    if job in valid_jobs and seq in valid_jobs:
        if job != seq: 
            G.add_edge(seq, job)

all_job_names = sorted(list(set(G.nodes)))

try:
    cycles = list(nx.simple_cycles(G))
except nx.NetworkXError as e:
    st.error(f"❌ Error: Struktur data graph bermasalah setelah pembersihan. Detail: {e}")
    st.stop()

if cycles:
    st.error("🚨 KRITIS: TERDETEKSI CIRCULAR DEPENDENCY!")
    st.markdown("Visualisasi **masih gagal** karena adanya **loop** dalam data Anda. Mohon perbaiki data.")
    for i, cycle in enumerate(cycles[:5]): 
        st.code(f"Loop {i+1}: {' -> '.join(cycle)} -> {cycle[0]}", language='python')
    st.stop() 


# --- Graph Functions (Caching) ---
@st.cache_data
def get_descendant_count(_G, root):
    return len(nx.descendants(_G, root)) + 1 

def build_tree(G, root):
    count = get_descendant_count(G, root) 
    label = f"{root} ({count})"
    children = list(G.successors(root))
    
    if not children:
        return {"label": label, "value": root}
        
    return {
        "label": label,
        "value": root,
        "children": [build_tree(G, c) for c in children]
    }

def get_expansion_path(G, target_job):
    all_roots = [node for node in G.nodes if not list(G.predecessors(node))]
    root_of_hierarchy = target_job
    if all_roots:
        root_of_hierarchy = all_roots[0]
    try:
        path = nx.shortest_path(G, source=root_of_hierarchy, target=target_job)
        return path[:-1] 
    except nx.NetworkXNoPath:
        return [target_job] 
    except:
         return [target_job]

def get_full_subgraph(G, root):
    descendants = nx.descendants(G, root)
    sub_nodes = [root] + list(descendants)
    return G.subgraph(sub_nodes)

def get_full_predecessor_subgraph(G, root):
    predecessors = nx.ancestors(G, root)
    sub_nodes = list(predecessors) + [root]
    return G.subgraph(sub_nodes)


# -----------------
# === 3. Layout dan UI Utama ===
# -----------------
st.title("👨‍💼 Job Hierarchy Viewer Datastage")

col_tree, col_graph = st.columns([0.35, 0.65])

# --- Kolom Kiri ---
with col_tree:
    st.subheader("🔍 Kontrol & Hierarki")

    search_job_input = st.text_input("1. Masukkan Job (Fuzzy Search):", key="search_input")

    if 'selected_job' not in st.session_state: st.session_state['selected_job'] = None
    if 'job_to_expand' not in st.session_state: st.session_state['job_to_expand'] = None
    if 'expanded_nodes' not in st.session_state: st.session_state['expanded_nodes'] = []

    primary_root_job = st.session_state['selected_job']

    if search_job_input:
        search_job = search_job_input.strip()
        matches = process.extract(search_job, all_job_names, limit=10)
        good_matches = [match[0] for match in matches if match[1] >= 70]

        if good_matches:
            st.success(f"Ditemukan {len(good_matches)} Job yang mirip. Klik tombol:")
            button_cols = st.columns(min(len(good_matches), 3))
            
            for i, job_name in enumerate(good_matches):
                if button_cols[i % 3].button(f"➡️ **{job_name}**", key=f"btn_{job_name}"):
                    st.session_state['graph_control_node'] = None
                    st.session_state['selected_job'] = job_name
                    st.session_state['job_to_expand'] = job_name 
                    st.rerun() 
        else:
            st.error(f"Tidak ditemukan Job yang mirip dengan '**{search_job}**'.")
            
    st.markdown("---")
    
    # --- Tree Folding untuk Job Terpilih ---
    if primary_root_job:
        st.subheader("2. Hasil Hierarki (Tree Folding)")
        st.caption(f"Job Terpilih: **{primary_root_job}**")
        
        job_for_auto_expand = st.session_state.get('job_to_expand')
        if job_for_auto_expand and job_for_auto_expand == primary_root_job:
            expanded_paths = get_expansion_path(G, primary_root_job)
            st.session_state['expanded_nodes'] = expanded_paths
            st.session_state['job_to_expand'] = None 
        
        expanded_nodes = st.session_state.get('expanded_nodes', [primary_root_job])
        
        try:
            tree_data = [build_tree(G, primary_root_job)]
            selected = tree_select(
                tree_data, 
                expand_on_click=True, 
                key="tree_selector",
                expanded=expanded_nodes
            )
            
            if 'value' in selected and selected['value']:
                selected_tree_node = selected['value'][0] 
                st.caption(f"Node Graph Root saat ini: `{selected_tree_node}`")
                st.session_state['graph_control_node'] = selected_tree_node
            else:
                 st.session_state['graph_control_node'] = None
            
        except Exception as e:
            st.error(f"❌ Error saat menampilkan Tree Folding: {e}")
    else:
        st.info("Gunakan pencarian di atas atau Daftar Job di bawah.")
        
 # --- Fitur Foldering Turunan Job (Full Expand/Collapse + Full Download CSV) ---
st.markdown("---")
st.subheader("📁 Turunan Job (Expandable Folder Style)")

if primary_root_job:
    subG = get_full_subgraph(G, primary_root_job)

    if "expand_all_desc" not in st.session_state:
        st.session_state.expand_all_desc = False

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔽 Expand All Turunan"):
            st.session_state.expand_all_desc = True
    with col2:
        if st.button("🔼 Collapse All Turunan"):
            st.session_state.expand_all_desc = False
    with col3:
        # === Tombol download full hierarchy ===
        all_edges = list(nx.edge_dfs(G, source=primary_root_job))
        if all_edges:
            df_full = pd.DataFrame(all_edges, columns=["Parent", "Child"])
            df_full.insert(0, "Root", primary_root_job)

            csv_full = df_full.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"📥 Download Semua Turunan `{primary_root_job}` (Full Hierarchy CSV)",
                data=csv_full,
                file_name=f"full_hierarchy_{primary_root_job.replace(' ', '_')}.csv",
                mime="text/csv"
            )

    # === Build struktur pohon ===
    def build_desc_tree(G, root):
        children = sorted(list(G.successors(root)))
        if not children:
            return {"label": f"📄 {root}", "value": root}
        else:
            return {
                "label": f"📁 {root} ({len(children)})",
                "value": root,
                "children": [build_desc_tree(G, c) for c in children]
            }

    try:
        desc_tree_data = [build_desc_tree(G, primary_root_job)]
        st.caption(f"Klik folder untuk buka/tutup turunan dari **{primary_root_job}**")

        # === Atur node yang diexpand ===
        if st.session_state.expand_all_desc:
            all_expanded_nodes = list(nx.descendants(G, primary_root_job)) + [primary_root_job]
        else:
            all_expanded_nodes = []

        selected_desc = tree_select(
            desc_tree_data,
            expand_on_click=True,
            check_model="leaf",
            only_leaf_checkboxes=False,
            key="desc_tree_view",
            expanded=all_expanded_nodes,
        )

        selected_last_node = None
        if selected_desc:
            if "checked" in selected_desc and selected_desc["checked"]:
                selected_last_node = selected_desc["checked"][-1]
            elif "value" in selected_desc and selected_desc["value"]:
                selected_last_node = selected_desc["value"][-1]

        # === Jika user klik node tertentu ===
        if selected_last_node:
            st.success(f"📂 Node terakhir dibuka/dipilih: `{selected_last_node}`")

            descendants_last = sorted(list(nx.descendants(G, selected_last_node)))
            df_last_desc = pd.DataFrame({
                "Root Job": selected_last_node,
                "Descendant Job": descendants_last
            })

            st.caption(f"Total turunan: {len(descendants_last)} jobs")

            if not df_last_desc.empty:
                csv_desc = df_last_desc.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Download Turunan `{selected_last_node}` (CSV)",
                    data=csv_desc,
                    file_name=f"descendants_{selected_last_node.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Job ini tidak memiliki turunan lebih lanjut.")

        # === Kalau belum klik node tapi Expand All aktif ===
        elif st.session_state.expand_all_desc:
            descendants_root = sorted(list(nx.descendants(G, primary_root_job)))
            df_root_desc = pd.DataFrame({
                "Root Job": primary_root_job,
                "Descendant Job": descendants_root
            })

            if not df_root_desc.empty:
                csv_root = df_root_desc.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Download Semua Turunan `{primary_root_job}` (CSV)",
                    data=csv_root,
                    file_name=f"all_descendants_{primary_root_job.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
                st.caption(f"Total {len(descendants_root)} turunan dari {primary_root_job}")
            else:
                st.info("Tidak ada turunan ditemukan untuk job ini.")

        else:
            st.info("Klik node untuk melihat dan unduh turunannya.")

    except Exception as e:
        st.error(f"❌ Error saat menampilkan turunan job: {e}")

    st.markdown("---")

    # --- Daftar Semua Job ---
    st.subheader(f"3. Daftar Semua Job ({len(all_job_names)} Jobs)")
    with st.expander("📚 Klik untuk Menampilkan dan Memilih Job", expanded=False):
        selected_job_from_list = st.selectbox(
            "Pilih Job Root:",
            options=["-- Pilih Job --"] + all_job_names,
            key="list_selector"
        )

        if selected_job_from_list != "-- Pilih Job --":
            if selected_job_from_list != st.session_state.get('selected_job'):
                st.session_state['selected_job'] = selected_job_from_list
                st.session_state['job_to_expand'] = selected_job_from_list
                st.session_state['graph_control_node'] = None
                st.rerun()

# --- Kolom Kanan: Visualisasi Graph Interaktif ---
with col_graph:
    st.subheader("📊 Visualisasi Interaktif")
    
    if primary_root_job:
        control_node = st.session_state.get('graph_control_node')
        graph_root_unsafe = control_node if control_node and isinstance(control_node, str) else primary_root_job
        
        if graph_root_unsafe is None:
             st.info("Pilih Job di kolom kiri untuk melihat visualisasi.")
             st.stop()
             
        graph_root = str(graph_root_unsafe) 
        st.markdown(f"**Node Graph Root yang divisualisasikan:** `{graph_root}`")
        
        try:
            view_mode = st.radio(
                "Pilih Tampilan Graph:",
                ["Keturunan (Descendants) Saja", "Asal Muasal (Predecessors) Saja"],
                index=0,
                key="graph_view_mode"
            )
            
            if view_mode == "Keturunan (Descendants) Saja":
                subG = get_full_subgraph(G, graph_root)
                info_text = "Job ini dan semua keturunannya."
            else: 
                subG = get_full_predecessor_subgraph(G, graph_root)
                info_text = "Job ini dan semua asal muasalnya."
            
            st.info(f"Mode Graph Interaktif. {info_text} Total **{subG.number_of_nodes()}** jobs.")

            net = Network(height="600px", width="100%", directed=True, bgcolor="#f8f9fa", font_color="#212529")

            tempG = subG.copy() 
            for u, v, d in tempG.edges(data=True):
                d.clear() 
            
            net.from_nx(tempG)
            
            for node in net.nodes:
                node['color'] = "#007bff"
                node['size'] = 15
            
            if graph_root in subG.nodes:
                for node in net.nodes:
                    if node['id'] == graph_root:
                        node['color'] = "#dc3545"
                        node['size'] = 25
                        node['title'] = "Root Job (Fokus)"
                        break 
            
            net.show_buttons(filter_=['physics'])
            html_file_name = f"dependency_graph_{graph_root.replace(' ', '_')}.html"
            net.save_graph(html_file_name)
            
            if os.path.exists(html_file_name):
                 with open(html_file_name, "r", encoding="utf-8") as f:
                    html_content = f.read()
                    components.html(html_content, height=650, scrolling=True) 
            else:
                st.error("Gagal membaca file HTML untuk Pyvis.")

            with open(html_file_name, "rb") as f:
                st.download_button(
                    label="⬇️ Download Graph (HTML)",
                    data=f,
                    file_name=html_file_name,
                    mime="text/html"
                )

        except Exception as e:
            st.error(f"❌ Terjadi error tak terduga saat menampilkan visualisasi. Detail: {e}")
            st.warning("Mohon **refresh Streamlit (Ctrl+R atau R)** dan coba lagi.")
            
    else:
        st.info("Pilih Job di kolom kiri untuk melihat visualisasi Graph.")
