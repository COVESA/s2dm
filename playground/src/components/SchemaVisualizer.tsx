import type { GraphQLSchema } from "graphql";
import { buildSchema } from "graphql";
import { Voyager } from "graphql-voyager";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Component, type ReactNode, useEffect, useState } from "react";
import "graphql-voyager/dist/voyager.css";
import "@/components/voyager-dark.css";
import { ErrorDisplay } from "@/components/ErrorDisplay";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Heading } from "@/components/ui/heading";
import { getErrorMessage } from "@/utils/getErrorMessage";

type SchemaVisualizerProps = {
	schema: string;
};

// Material UI renders menus, popovers and tooltips into portals at the body.
const MUI_PORTAL_SELECTOR =
	".MuiModal-root, .MuiPopover-root, .MuiPopper-root, .MuiTooltip-popper";

// A click in a portalled menu is inside the dialog, as the user sees it.
function keepOpenForPortalledMenus(event: Event) {
	const target = event.target instanceof Element ? event.target : null;
	const portal = target?.closest(MUI_PORTAL_SELECTOR);
	if (portal) {
		event.preventDefault();
	}
}

const VISUALIZER_FAILURE_MESSAGE = "The schema graph could not be displayed.";

/**
 * Catches errors that Voyager throws while rendering the schema graph and
 * shows an error message in place of the visualizer.
 */
class VoyagerErrorBoundary extends Component<
	{ children: ReactNode },
	{ hasFailed: boolean }
> {
	state = { hasFailed: false };

	static getDerivedStateFromError() {
		return { hasFailed: true };
	}

	render() {
		if (this.state.hasFailed) {
			return <ErrorDisplay error={VISUALIZER_FAILURE_MESSAGE} />;
		}
		return this.props.children;
	}
}

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
			setError(getErrorMessage(err));
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
			<VoyagerErrorBoundary key={schema}>
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
			</VoyagerErrorBoundary>
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
			{/* Non-modal: a modal dialog's focus trap and pointer-events lock fight the
			    portalled Material UI menu. Radix drops its overlay too, so this stands in. */}
			{isFullscreen && (
				<div aria-hidden className="fixed inset-0 z-40 bg-black/50" />
			)}
			<Dialog modal={false} open={isFullscreen} onOpenChange={setIsFullscreen}>
				<DialogContent
					className="flex h-[90vh] w-[90vw] max-w-none flex-col p-0 sm:max-w-none"
					onInteractOutside={keepOpenForPortalledMenus}
				>
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
