import type { GraphQLSchema } from "graphql";
import { buildSchema } from "graphql";
import { Voyager } from "graphql-voyager";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import "graphql-voyager/dist/voyager.css";
import "@/components/voyager-dark.css";
import { Button } from "@/components/ui/button";
import { Heading } from "@/components/ui/heading";
import { cn } from "@/utils/cn";

type SchemaVisualizerProps = {
	schema: string;
};

export function SchemaVisualizer({ schema }: SchemaVisualizerProps) {
	const [graphqlSchema, setGraphqlSchema] = useState<GraphQLSchema | null>(
		null,
	);
	const [error, setError] = useState<string>("");
	const [docsCollapsed, setDocsCollapsed] = useState(true);
	const [blockCount, setBlockCount] = useState<number | null>(null);
	const containerRef = useRef<HTMLDivElement | null>(null);

	useEffect(() => {
		if (!schema.trim()) {
			setBlockCount(null);
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

	useEffect(() => {
		const container = containerRef.current;

		if (!container || !graphqlSchema) {
			setBlockCount(null);
			return;
		}

		const updateBlockCount = () => {
			const count = container.querySelectorAll(".graphql-voyager svg g.node").length;
			setBlockCount(count > 0 ? count : null);
		};

		updateBlockCount();

		const observer = new MutationObserver(() => {
			updateBlockCount();
		});

		observer.observe(container, {
			childList: true,
			subtree: true,
		});

		return () => {
			observer.disconnect();
		};
	}, [graphqlSchema]);

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

	const shouldForceDocsOpen = blockCount === 1;

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
		<div ref={containerRef} className="relative h-full w-full">
			<Voyager
				introspection={graphqlSchema}
				displayOptions={{
					skipRelay: true,
					skipDeprecated: true,
					showLeafFields: true,
				}}
				hideDocs={shouldForceDocsOpen ? false : docsCollapsed}
				hideSettings={false}
			/>
			{!shouldForceDocsOpen && (
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
			)}
		</div>
	);
}
