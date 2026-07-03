from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Set


@dataclass(frozen=True)
class FamilyMember:
	member_id: str
	name: str
	gender: str
	age: int

	def to_dict(self) -> Dict[str, object]:
		return asdict(self)


class FamilyTree:
	def __init__(self) -> None:
		self.members: Dict[str, FamilyMember] = {}
		self.parent_to_children: Dict[str, Set[str]] = {}
		self.child_to_parents: Dict[str, Set[str]] = {}
		self.spouses: Dict[str, Set[str]] = {}
		self.siblings: Dict[str, Set[str]] = {}

	def add_member(self, member_id: str, name: str, gender: str, age: int) -> FamilyMember:
		member_id = member_id.strip()
		name = name.strip()
		gender = gender.strip()

		if not member_id:
			raise ValueError("member_id must be non-empty")
		if not name:
			raise ValueError("name must be non-empty")
		if age < 0:
			raise ValueError("age must be zero or greater")
		if member_id in self.members:
			raise ValueError(f"member_id '{member_id}' already exists")

		member = FamilyMember(member_id=member_id, name=name, gender=gender, age=age)
		self.members[member_id] = member
		self.parent_to_children.setdefault(member_id, set())
		self.child_to_parents.setdefault(member_id, set())
		self.spouses.setdefault(member_id, set())
		self.siblings.setdefault(member_id, set())
		return member

	def add_parent_child(self, parent_id: str, child_id: str) -> None:
		self._ensure_distinct_known_members(parent_id, child_id)
		self.parent_to_children[parent_id].add(child_id)
		self.child_to_parents[child_id].add(parent_id)

		for existing_sibling_id in self.parent_to_children[parent_id]:
			if existing_sibling_id != child_id:
				self.add_sibling(existing_sibling_id, child_id)

	def add_spouse(self, member_a_id: str, member_b_id: str) -> None:
		self._ensure_distinct_known_members(member_a_id, member_b_id)
		self.spouses[member_a_id].add(member_b_id)
		self.spouses[member_b_id].add(member_a_id)

	def add_sibling(self, member_a_id: str, member_b_id: str) -> None:
		self._ensure_distinct_known_members(member_a_id, member_b_id)
		self.siblings[member_a_id].add(member_b_id)
		self.siblings[member_b_id].add(member_a_id)

	def get_member(self, member_id: str) -> FamilyMember:
		self._ensure_member_exists(member_id)
		return self.members[member_id]

	def get_children(self, member_id: str) -> List[FamilyMember]:
		self._ensure_member_exists(member_id)
		return self._sorted_members(self.parent_to_children[member_id])

	def get_parents(self, member_id: str) -> List[FamilyMember]:
		self._ensure_member_exists(member_id)
		return self._sorted_members(self.child_to_parents[member_id])

	def get_spouses(self, member_id: str) -> List[FamilyMember]:
		self._ensure_member_exists(member_id)
		return self._sorted_members(self.spouses[member_id])

	def get_siblings(self, member_id: str) -> List[FamilyMember]:
		self._ensure_member_exists(member_id)
		return self._sorted_members(self.siblings[member_id])

	def to_dict(self) -> Dict[str, object]:
		return {
			"members": [member.to_dict() for member in sorted(self.members.values(), key=lambda item: item.member_id)],
			"relationships": {
				"parent_child": self._serialize_edge_map(self.parent_to_children),
				"spouse": self._serialize_edge_map(self.spouses),
				"sibling": self._serialize_edge_map(self.siblings),
			},
		}

	@classmethod
	def from_dict(cls, payload: Dict[str, object]) -> "FamilyTree":
		tree = cls()
		members = payload.get("members", [])
		relationships = payload.get("relationships", {})

		for member_payload in members:
			tree.add_member(
				member_id=str(member_payload["member_id"]),
				name=str(member_payload["name"]),
				gender=str(member_payload["gender"]),
				age=int(member_payload["age"]),
			)

		for parent_id, child_ids in relationships.get("parent_child", {}).items():
			for child_id in child_ids:
				tree.add_parent_child(parent_id, child_id)

		for member_id, spouse_ids in relationships.get("spouse", {}).items():
			for spouse_id in spouse_ids:
				if member_id < spouse_id:
					tree.add_spouse(member_id, spouse_id)

		for member_id, sibling_ids in relationships.get("sibling", {}).items():
			for sibling_id in sibling_ids:
				if member_id < sibling_id:
					tree.add_sibling(member_id, sibling_id)

		return tree

	def save_json(self, path: str | Path) -> Path:
		target_path = Path(path)
		with target_path.open("w", encoding="utf-8") as handle:
			json.dump(self.to_dict(), handle, indent=2)
		return target_path

	@classmethod
	def load_json(cls, path: str | Path) -> "FamilyTree":
		source_path = Path(path)
		with source_path.open("r", encoding="utf-8") as handle:
			payload = json.load(handle)
		return cls.from_dict(payload)

	def render_text(self) -> str:
		lines: List[str] = []
		for member in sorted(self.members.values(), key=lambda item: item.member_id):
			parents = self._format_member_names(self.child_to_parents[member.member_id])
			children = self._format_member_names(self.parent_to_children[member.member_id])
			spouses = self._format_member_names(self.spouses[member.member_id])
			siblings = self._format_member_names(self.siblings[member.member_id])
			lines.extend(
				[
					f"{member.member_id}: {member.name} ({member.gender}, age {member.age})",
					f"  parents : {parents}",
					f"  children: {children}",
					f"  spouses : {spouses}",
					f"  siblings: {siblings}",
				]
			)
		return "\n".join(lines)

	def render_mermaid(self) -> str:
		lines = ["flowchart TD"]
		for member in sorted(self.members.values(), key=lambda item: item.member_id):
			label = self._escape_label(f"{member.name}\\n{member.gender}, {member.age}")
			lines.append(f"    {member.member_id}[\"{label}\"]")

		for parent_id in sorted(self.parent_to_children):
			for child_id in sorted(self.parent_to_children[parent_id]):
				lines.append(f"    {parent_id} -->|parent| {child_id}")

		for member_id in sorted(self.spouses):
			for spouse_id in sorted(self.spouses[member_id]):
				if member_id < spouse_id:
					lines.append(f"    {member_id} -. spouse .- {spouse_id}")

		for member_id in sorted(self.siblings):
			for sibling_id in sorted(self.siblings[member_id]):
				if member_id < sibling_id:
					lines.append(f"    {member_id} -. sibling .- {sibling_id}")

		return "\n".join(lines)

	def render_graphviz(self) -> str:
		lines = ["digraph FamilyTree {", "  rankdir=TB;", '  node [shape=box, style="rounded"];']
		generation_levels = self._generation_levels()
		members_by_generation: Dict[int, List[str]] = {}
		for member_id, generation in generation_levels.items():
			members_by_generation.setdefault(generation, []).append(member_id)

		for member in sorted(self.members.values(), key=lambda item: item.member_id):
			label = self._escape_label(f"{member.name}\\n{member.gender}, {member.age}")
			lines.append(f'  {member.member_id} [label="{label}"];')

		for generation in sorted(members_by_generation):
			member_ids = " ".join(sorted(members_by_generation[generation]))
			lines.append(f"  {{ rank=same; {member_ids}; }}")

		for parent_id in sorted(self.parent_to_children):
			for child_id in sorted(self.parent_to_children[parent_id]):
				lines.append(f'  {parent_id} -> {child_id} [label="parent"];')

		for member_id in sorted(self.spouses):
			for spouse_id in sorted(self.spouses[member_id]):
				if member_id < spouse_id:
					lines.append(f'  {member_id} -> {spouse_id} [dir=both, style=dashed, label="spouse"];')

		for member_id in sorted(self.siblings):
			for sibling_id in sorted(self.siblings[member_id]):
				if member_id < sibling_id:
					lines.append(f'  {member_id} -> {sibling_id} [dir=both, style=dotted, label="sibling"];')

		lines.append("}")
		return "\n".join(lines)

	def _generation_levels(self) -> Dict[str, int]:
		indegree: Dict[str, int] = {member_id: len(self.child_to_parents[member_id]) for member_id in self.members}
		generation_levels: Dict[str, int] = {member_id: 0 for member_id in self.members}
		queue: List[str] = sorted(member_id for member_id, degree in indegree.items() if degree == 0)
		index = 0
		processed: Set[str] = set()

		while index < len(queue):
			parent_id = queue[index]
			index += 1
			processed.add(parent_id)

			for child_id in sorted(self.parent_to_children[parent_id]):
				generation_levels[child_id] = max(generation_levels[child_id], generation_levels[parent_id] + 1)
				indegree[child_id] -= 1
				if indegree[child_id] == 0:
					queue.append(child_id)

		for member_id in sorted(self.members):
			if member_id not in processed:
				generation_levels[member_id] = 0

		return generation_levels

	def to_cytoscape(self) -> Dict[str, List[Dict[str, object]]]:
		nodes = []
		edges = []

		for member in sorted(self.members.values(), key=lambda item: item.member_id):
			nodes.append(
				{
					"data": {
						"id": member.member_id,
						"label": member.name,
						"gender": member.gender,
						"age": member.age,
					}
				}
			)

		for parent_id in sorted(self.parent_to_children):
			for child_id in sorted(self.parent_to_children[parent_id]):
				edges.append(
					{
						"data": {
							"id": f"parent-{parent_id}-{child_id}",
							"source": parent_id,
							"target": child_id,
							"relationship": "parent",
						}
					}
				)

		for member_id in sorted(self.spouses):
			for spouse_id in sorted(self.spouses[member_id]):
				if member_id < spouse_id:
					edges.append(
						{
							"data": {
								"id": f"spouse-{member_id}-{spouse_id}",
								"source": member_id,
								"target": spouse_id,
								"relationship": "spouse",
							}
						}
					)

		for member_id in sorted(self.siblings):
			for sibling_id in sorted(self.siblings[member_id]):
				if member_id < sibling_id:
					edges.append(
						{
							"data": {
								"id": f"sibling-{member_id}-{sibling_id}",
								"source": member_id,
								"target": sibling_id,
								"relationship": "sibling",
							}
						}
					)

		return {"nodes": nodes, "edges": edges}

	def to_cytoscape_cyjs(self) -> Dict[str, object]:
		return {"elements": self.to_cytoscape()}

	def to_family_tree_viz(self, guild_id: Optional[int] = None) -> Dict[str, object]:
		try:
			import family_tree_viz as ftv
		except ImportError as error:
			raise ImportError("family_tree_viz is required for this conversion") from error

		member_ids = sorted(self.members)
		numeric_ids = {member_id: index + 1 for index, member_id in enumerate(member_ids)}
		resolved_guild_id = guild_id if guild_id is not None else (abs(hash(tuple(member_ids))) % 1_000_000_000) + 1
		ftv_members: Dict[str, object] = {}

		for member_id in member_ids:
			member = self.members[member_id]
			ftv_members[member_id] = ftv.FamilyTreeMember(
				id=numeric_ids[member_id],
				guild_id=resolved_guild_id,
				label=member.name,
			)

		for parent_id in sorted(self.parent_to_children):
			parent = ftv_members[parent_id]
			for child_id in sorted(self.parent_to_children[parent_id]):
				child_numeric_id = numeric_ids[child_id]
				parent.add_child(child_numeric_id)
				child = ftv_members[child_id]
				if child.parent is None:
					child.parent = numeric_ids[parent_id]

		for member_id in sorted(self.spouses):
			for spouse_id in sorted(self.spouses[member_id]):
				if member_id < spouse_id:
					ftv_members[member_id].add_partner(numeric_ids[spouse_id])
					ftv_members[spouse_id].add_partner(numeric_ids[member_id])

		for member_id in sorted(self.siblings):
			for sibling_id in sorted(self.siblings[member_id]):
				if member_id < sibling_id:
					ftv_members[member_id].add_friend(numeric_ids[sibling_id])
					ftv_members[sibling_id].add_friend(numeric_ids[member_id])

		root_candidates = [member_id for member_id in member_ids if not self.child_to_parents[member_id]]
		default_root_member_id = root_candidates[0] if root_candidates else (member_ids[0] if member_ids else None)
		return {
			"members": ftv_members,
			"numeric_ids": numeric_ids,
			"guild_id": resolved_guild_id,
			"default_root_member_id": default_root_member_id,
		}

	def render_family_tree_viz(
		self,
		path: str | Path,
		root_member_id: Optional[str] = None,
		tree_type: str = "QUICK",
		image_format: str = "png",
		direction: Literal["TB", "LR"] = "TB",
	) -> Path:
		try:
			import family_tree_viz as ftv
		except ImportError as error:
			raise ImportError("family_tree_viz is required for this renderer") from error

		converted = self.to_family_tree_viz()
		members = converted["members"]
		if not members:
			raise ValueError("Cannot render an empty family tree")

		selected_root_member_id = root_member_id or converted["default_root_member_id"]
		if selected_root_member_id not in members:
			raise KeyError(f"Unknown member_id '{selected_root_member_id}'")

		if shutil.which("dot") is None:
			raise RuntimeError("Graphviz executable 'dot' is required for family_tree_viz rendering")

		tree_type_value = getattr(ftv.TreeType, tree_type.upper(), None)
		if tree_type_value is None:
			raise ValueError(f"Unknown tree_type '{tree_type}'")

		resolved_direction = direction.upper()
		if resolved_direction not in {"TB", "LR"}:
			raise ValueError("direction must be 'TB' or 'LR'")

		target_path = Path(path)
		current_user = members[selected_root_member_id]
		ftv.CustomisedTreeUser.get_by_id(current_user.id).direction = resolved_direction
		generator = ftv.FamilyTreeGenerator()
		output = asyncio.run(
			generator.generate(
				current_user=current_user,
				tree_type=tree_type_value,
				image_format=image_format,
				output_path=str(target_path),
			)
		)

		if output is None:
			raise RuntimeError("family_tree_viz did not return any rendered output")

		if target_path.exists():
			return target_path

		resolved_output_path = target_path if target_path.suffix else target_path.with_suffix(f".{image_format}")
		if not resolved_output_path.exists():
			output.save(str(resolved_output_path))
		return resolved_output_path

	def render_sif(self) -> str:
		lines: List[str] = []

		for parent_id in sorted(self.parent_to_children):
			for child_id in sorted(self.parent_to_children[parent_id]):
				lines.append(f"{parent_id}\tparent\t{child_id}")

		for member_id in sorted(self.spouses):
			for spouse_id in sorted(self.spouses[member_id]):
				if member_id < spouse_id:
					lines.append(f"{member_id}\tspouse\t{spouse_id}")

		for member_id in sorted(self.siblings):
			for sibling_id in sorted(self.siblings[member_id]):
				if member_id < sibling_id:
					lines.append(f"{member_id}\tsibling\t{sibling_id}")

		return "\n".join(lines)

	def render_edges_tsv(self) -> str:
		lines = ["source\tinteraction\ttarget"]
		for edge in self.to_cytoscape()["edges"]:
			edge_data = edge["data"]
			lines.append(f"{edge_data['source']}\t{edge_data['relationship']}\t{edge_data['target']}")
		return "\n".join(lines)

	def write_mermaid_html(self, path: str | Path, title: str = "Family Tree") -> Path:
		target_path = Path(path)
		mermaid = self.render_mermaid()
		html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title}</title>
  <script type=\"module\">
	import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
	mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
  </script>
  <style>
	body {{ font-family: Georgia, serif; margin: 2rem; background: #f4efe6; color: #2b2118; }}
	.mermaid {{ background: white; border-radius: 12px; padding: 1rem; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08); }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class=\"mermaid\">
{mermaid}
  </div>
</body>
</html>
"""
		with target_path.open("w", encoding="utf-8") as handle:
			handle.write(html)
		return target_path

	def _sorted_members(self, member_ids: Iterable[str]) -> List[FamilyMember]:
		return [self.members[member_id] for member_id in sorted(member_ids)]

	def _ensure_member_exists(self, member_id: str) -> None:
		if member_id not in self.members:
			raise KeyError(f"Unknown member_id '{member_id}'")

	def _ensure_distinct_known_members(self, first_member_id: str, second_member_id: str) -> None:
		self._ensure_member_exists(first_member_id)
		self._ensure_member_exists(second_member_id)
		if first_member_id == second_member_id:
			raise ValueError("relationships require two different members")

	def _format_member_names(self, member_ids: Iterable[str]) -> str:
		if not member_ids:
			return "-"
		return ", ".join(self.members[member_id].name for member_id in sorted(member_ids))

	def _serialize_edge_map(self, edge_map: Dict[str, Set[str]]) -> Dict[str, List[str]]:
		return {member_id: sorted(neighbor_ids) for member_id, neighbor_ids in sorted(edge_map.items()) if neighbor_ids}

	def _escape_label(self, label: str) -> str:
		return label.replace('"', '\\"')


def build_sample_tree() -> FamilyTree:
	tree = FamilyTree()
	tree.add_member("john", "John Carter", "male", 68)
	tree.add_member("maria", "Maria Carter", "female", 65)
	tree.add_member("anna", "Anna Carter", "female", 40)
	tree.add_member("miles", "Miles Carter", "male", 37)
	tree.add_member("zoe", "Zoe Carter", "female", 8)
	tree.add_spouse("john", "maria")
	tree.add_parent_child("john", "anna")
	tree.add_parent_child("maria", "anna")
	tree.add_parent_child("john", "miles")
	tree.add_parent_child("maria", "miles")
	tree.add_parent_child("anna", "zoe")
	return tree


def interactive_cli(data_path: Path) -> None:
	tree = FamilyTree.load_json(data_path) if data_path.exists() else FamilyTree()

	menu = (
		"\nChoose an action:\n"
		"  1. Add member\n"
		"  2. Add parent/child relationship\n"
		"  3. Add spouse relationship\n"
		"  4. Add sibling relationship\n"
		"  5. Show text tree\n"
		"  6. Export Mermaid HTML\n"
		"  7. Save and exit\n"
	)

	while True:
		print(menu)
		choice = input("Selection: ").strip()

		if choice == "1":
			member_id = input("member id: ").strip()
			name = input("name: ").strip()
			gender = input("gender: ").strip()
			age = int(input("age: ").strip())
			tree.add_member(member_id, name, gender, age)
		elif choice == "2":
			parent_id = input("parent member id: ").strip()
			child_id = input("child member id: ").strip()
			tree.add_parent_child(parent_id, child_id)
		elif choice == "3":
			member_a_id = input("first spouse id: ").strip()
			member_b_id = input("second spouse id: ").strip()
			tree.add_spouse(member_a_id, member_b_id)
		elif choice == "4":
			member_a_id = input("first sibling id: ").strip()
			member_b_id = input("second sibling id: ").strip()
			tree.add_sibling(member_a_id, member_b_id)
		elif choice == "5":
			print()
			print(tree.render_text())
		elif choice == "6":
			export_path = data_path.with_suffix(".html")
			tree.write_mermaid_html(export_path)
			print(f"Wrote Mermaid visualization to {export_path}")
		elif choice == "7":
			tree.save_json(data_path)
			print(f"Saved family tree to {data_path}")
			return
		else:
			print("Unknown selection")


def main(argv: Optional[List[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="Simple family tree database and renderer")
	parser.add_argument("--data", default="family_tree.json", help="JSON file used to persist the family tree")
	parser.add_argument("--sample", action="store_true", help="Write a sample family tree to the data file")
	parser.add_argument("--render", choices=["text", "mermaid", "graphviz", "cytoscape", "html"], help="Render the stored family tree")
	parser.add_argument("--interactive", action="store_true", help="Launch the interactive entry prompt")
	args = parser.parse_args(argv)

	data_path = Path(args.data)

	if args.sample:
		tree = build_sample_tree()
		tree.save_json(data_path)
		print(f"Wrote sample family tree to {data_path}")
		return 0

	if args.interactive:
		interactive_cli(data_path)
		return 0

	if args.render:
		tree = FamilyTree.load_json(data_path)
		if args.render == "text":
			print(tree.render_text())
		elif args.render == "mermaid":
			print(tree.render_mermaid())
		elif args.render == "graphviz":
			print(tree.render_graphviz())
		elif args.render == "cytoscape":
			print(json.dumps(tree.to_cytoscape(), indent=2))
		elif args.render == "html":
			output_path = tree.write_mermaid_html(data_path.with_suffix(".html"))
			print(f"Wrote Mermaid visualization to {output_path}")
		return 0

	parser.print_help()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
