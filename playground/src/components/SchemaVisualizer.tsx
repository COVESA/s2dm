import type { GraphQLSchema } from "graphql";
import { buildSchema } from "graphql";
import { Voyager } from "graphql-voyager";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useEffect, useState } from "react";
import "graphql-voyager/dist/voyager.css";
import "@/components/voyager-dark.css";
import { Button } from "@/components/ui/button";
import { Heading } from "@/components/ui/heading";
import { cn } from "@/lib/utils";

type SchemaVisualizerProps = {
	schema: string;
};

export function SchemaVisualizer({ schema }: SchemaVisualizerProps) {
	const [graphqlSchema, setGraphqlSchema] = useState<GraphQLSchema | null>(
		null,
	);
	const [error, setError] = useState<string>("");
	const [docsCollapsed, setDocsCollapsed] = useState(true);

	useEffect(() => {
		if (!schema.trim()) {
			return;
		}

		const buildSchemaAsync = async () => {
			try {
				const builtSchema = buildSchema(schema);
				setGraphqlSchema(builtSchema);
				setError("");
			} catch (err) {
				setError(err instanceof Error ? err.message : String(err));
				setGraphqlSchema(null);
			}
		};

		buildSchemaAsync();
	}, [schema]);

	if (error) {
		return (
			<div className="p-8 text-destructive">
				<Heading level="h3" className="mb-4">
					Failed to parse schema:
				</Heading>
				<pre className="bg-destructive/10 p-4 rounded-lg overflow-auto">
					{error}
				</pre>
			</div>
		);
	}

	if (!graphqlSchema) {
		return (
			<div className="flex items-center justify-center h-full text-muted-foreground">
				<p>No schema to visualize</p>
			</div>
		);
	}

	let buttonIcon: React.ReactNode;
	let buttonTitle: string;

	if (docsCollapsed) {
		buttonIcon = <PanelRightClose className="h-4 w-4" />;
		buttonTitle = "Show docs panel";
	} else {
		buttonIcon = <PanelRightOpen className="h-4 w-4" />;
		buttonTitle = "Hide docs panel";
	}

	return (
		<div className="relative h-full w-full">
			<Voyager
				introspection={graphqlSchema}
				displayOptions={{
					skipRelay: true,
					skipDeprecated: true,
					showLeafFields: true,
				}}
				hideDocs={docsCollapsed}
				hideSettings={false}
			/>
			<Button
				variant="outline"
				size="icon"
				className={cn(
					"absolute bottom-2 left-2 z-10 !bg-background hover:!bg-muted",
				)}
				onClick={() => setDocsCollapsed((prev) => !prev)}
				title={buttonTitle}
			>
				{buttonIcon}
			</Button>
		</div>
	);
}
