from __future__ import annotations

import json
from pathlib import Path

from family_tree_pkg.family_tree import build_sample_tree


def main() -> int:
	tree = build_sample_tree()
	output_dir = Path("sample_outputs")
	output_dir.mkdir(exist_ok=True)

	json_path = output_dir / "family_tree.json"
	text_path = output_dir / "family_tree.txt"
	mermaid_path = output_dir / "family_tree.mmd"
	graphviz_path = output_dir / "family_tree.dot"
	cytoscape_path = output_dir / "family_tree_cytoscape.json"
	cyjs_path = output_dir / "family_tree_cytoscape.cyjs"
	sif_path = output_dir / "family_tree.sif"
	edges_tsv_path = output_dir / "family_tree_edges.tsv"
	ftv_path = output_dir / "family_tree_ftv.png"
	html_path = output_dir / "family_tree.html"

	tree.save_json(json_path)
	text_render = tree.render_text()
	mermaid_render = tree.render_mermaid()
	graphviz_render = tree.render_graphviz()
	cytoscape_render = tree.to_cytoscape()
	cyjs_render = tree.to_cytoscape_cyjs()
	sif_render = tree.render_sif()
	edges_tsv_render = tree.render_edges_tsv()
	tree.write_mermaid_html(html_path, title="Sample Family Tree")
	ftv_error = None
	ftv_output_path = None
	try:
		ftv_output_path = tree.render_family_tree_viz(ftv_path, image_format="png")
	except Exception as error:
		ftv_error = str(error)

	text_path.write_text(text_render + "\n", encoding="utf-8")
	mermaid_path.write_text(mermaid_render + "\n", encoding="utf-8")
	graphviz_path.write_text(graphviz_render + "\n", encoding="utf-8")
	cytoscape_path.write_text(json.dumps(cytoscape_render, indent=2) + "\n", encoding="utf-8")
	cyjs_path.write_text(json.dumps(cyjs_render, indent=2) + "\n", encoding="utf-8")
	sif_path.write_text(sif_render + "\n", encoding="utf-8")
	edges_tsv_path.write_text(edges_tsv_render + "\n", encoding="utf-8")

	print("=== Sample Family Tree (Text) ===")
	print(text_render)
	print()

	print("=== Mermaid ===")
	print(mermaid_render)
	print()

	print("=== Graphviz DOT ===")
	print(graphviz_render)
	print()

	print("=== Cytoscape JSON ===")
	print(json.dumps(cytoscape_render, indent=2))
	print()

	print("Wrote sample outputs to:")
	print(f"  {json_path}")
	print(f"  {text_path}")
	print(f"  {mermaid_path}")
	print(f"  {graphviz_path}")
	print(f"  {cytoscape_path}")
	print(f"  {cyjs_path}")
	print(f"  {sif_path}")
	print(f"  {edges_tsv_path}")
	if ftv_output_path:
		print(f"  {ftv_output_path}")
	elif ftv_error:
		print(f"  family_tree_viz render skipped: {ftv_error}")
	print(f"  {html_path}")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())