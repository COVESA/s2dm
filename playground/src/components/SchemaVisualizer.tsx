import type { GraphQLSchema } from "graphql";
import { buildSchema } from "graphql";
import { Voyager } from "graphql-voyager";
import { useEffect, useState } from "react";
import "graphql-voyager/dist/voyager.css";
import "@/components/voyager-dark.css";
import { Heading } from "@/components/ui/heading";

type SchemaVisualizerProps = {
	schema: string;
};

export function SchemaVisualizer({ schema }: SchemaVisualizerProps) {
	const [graphqlSchema, setGraphqlSchema] = useState<GraphQLSchema | null>(
		null,
	);
	const [error, setError] = useState<string>("");

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
				hideDocs={false}
				hideSettings={false}
			/>
		</div>
	);
}
