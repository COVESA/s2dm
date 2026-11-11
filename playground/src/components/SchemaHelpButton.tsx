import { Eye, Hammer, Layers, Package, Plus, Trash2 } from "lucide-react";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import { ThemeToggle } from "@/components/ThemeToggle";

export function SchemaToolbar() {
	return (
		<>
			<ThemeToggle />
			<HelpButton
				title="Schema Files & Dependencies"
				ariaLabel="Schema files help"
			>
				<HelpItem
					term={
						<>
							<Package className="inline h-4 w-4 align-text-bottom" /> Manage
							dependencies
						</>
					}
				>
					open the dependency manager to configure, resolve, and build external
					schema dependencies. Disabled while exploring a dependency.
				</HelpItem>
				<HelpItem
					term={
						<>
							<Plus className="inline h-4 w-4 align-text-bottom" /> Add schemas
						</>
					}
				>
					import schema files, a whole directory, or add a schema from a URL.
				</HelpItem>
				<HelpItem
					term={
						<>
							<Trash2 className="inline h-4 w-4 align-text-bottom" /> Remove all
							files
						</>
					}
				>
					clear every imported source file from the list.
				</HelpItem>
				<HelpItem term="Dependencies section">
					lists the resolved dependencies. Use{" "}
					<Hammer className="inline h-4 w-4 align-text-bottom" /> Build to
					compose them into a single schema (the dropdown offers Build and
					Auto-prefix), and <Eye className="inline h-4 w-4 align-text-bottom" />{" "}
					to preview that built dependency schema.
				</HelpItem>
				<HelpItem term="Files section">
					lists the imported source files. Drag entries to reorder them.
				</HelpItem>
				<HelpItem
					term={
						<>
							<Layers className="inline h-4 w-4 align-text-bottom" /> Compose
							and Validate
						</>
					}
				>
					validate and compose all source files into one schema. Tick “Include
					built dependencies in composition” to merge the built dependency
					schema into the result.
				</HelpItem>
			</HelpButton>
		</>
	);
}
