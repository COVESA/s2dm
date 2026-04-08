import type { GraphQLSchema } from "graphql";
import { buildSchema } from "graphql";
import { Voyager } from "graphql-voyager";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useEffect, useState } from "react";
import "graphql-voyager/dist/voyager.css";
import "@/components/voyager-dark.css";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Heading } from "@/components/ui/heading";

type SchemaVisualizerProps = {
	schema: string;
};

export function SchemaVisualizer({ schema }: SchemaVisualizerProps) {
	const [graphqlSchema, setGraphqlSchema] = useState<GraphQLSchema | null>(
		null,
	);
	const [error, setError] = useState<string>("");
	const [isFullscreen, setIsFullscreen] = useState(false);
	const [isDocsHidden, setIsDocsHidden] = useState(true);

	useEffect(() => {
		try {
			const builtSchema = buildSchema(schema);
			setGraphqlSchema(builtSchema);
			setError("");
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
			setGraphqlSchema(null);
		}
	}, [schema]);

	const renderContent = () => {
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

		return (
			<div className="relative h-full w-full">
				<Voyager
					introspection={graphqlSchema}
					displayOptions={{
						skipRelay: true,
						skipDeprecated: true,
						showLeafFields: true,
					}}
					hideDocs={isDocsHidden}
					hideSettings={false}
				/>
				<Button
					variant="outline"
					size="icon"
					className="absolute bottom-2 left-2 z-10 !bg-background hover:!bg-muted"
					onClick={() => setIsDocsHidden((previous) => !previous)}
					title={isDocsHidden ? "Show docs" : "Hide docs"}
				>
					{isDocsHidden ? (
						<PanelLeftOpen className="h-4 w-4" />
					) : (
						<PanelLeftClose className="h-4 w-4" />
					)}
				</Button>
			</div>
		);
	};

	return (
		<>
			<Button
				variant="outline"
				onClick={() => setIsFullscreen(true)}
				aria-label="Open schema visualizer"
				title="Open schema visualizer"
			>
				Open Visualizer
			</Button>
			<Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
				<DialogContent className="flex h-[90vh] w-[90vw] max-w-none flex-col p-0 sm:max-w-none">
					<DialogHeader className="shrink-0 border-b px-6 py-4">
						<DialogTitle>Schema Visualizer</DialogTitle>
					</DialogHeader>
					<div className="flex-1 min-h-0 overflow-hidden px-6 pb-6">
						{renderContent()}
					</div>
				</DialogContent>
			</Dialog>
		</>
	);
}
