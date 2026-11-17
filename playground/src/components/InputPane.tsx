import { LedgerOverview } from "@ledger-ui/components/LedgerOverview";
import { LedgerActions } from "@/components/ledger/LedgerActions";
import { LedgerFileList } from "@/components/ledger/LedgerFileList";
import { PANE_BOTTOM_PADDING, Pane } from "@/components/Pane";
import { ReleasesActions } from "@/components/releases/ReleasesActions";
import { ReleasesWorkspace } from "@/components/releases/ReleasesWorkspace";
import { SchemaActions } from "@/components/SchemaActions";
import { SchemaEditor } from "@/components/SchemaEditor";
import { SchemaSources } from "@/components/SchemaSources";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { selectExploringReleaseId } from "@/store/exploration/explorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectOriginalSchema,
	selectSourceFiles,
} from "@/store/schema/schemaSlice";
import {
	selectInputPaneCollapsed,
	selectWorkspace,
	setWorkspace,
	toggleInputPane,
	type Workspace,
} from "@/store/ui/uiSlice";

type InputPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function InputPane({
	position,
	collapsible,
	className = "bg-card",
}: InputPaneProps) {
	const dispatch = useAppDispatch();
	const originalSchema = useAppSelector(selectOriginalSchema);
	const isCollapsed = useAppSelector(selectInputPaneCollapsed);
	const files = useAppSelector(selectSourceFiles);
	const workspace = useAppSelector(selectWorkspace);
	const isLedger = workspace === "ledger";

	const exploringReleaseId = useAppSelector(selectExploringReleaseId);
	const isExploringRelease = exploringReleaseId !== null;

	let schemaEmptyMessage = "Nothing to display";
	if (files.length > 0) {
		schemaEmptyMessage =
			"Nothing to display. Click the compose button in the files section to start.";
	}

	let workspaceActions: React.ReactNode = <SchemaActions />;
	let body: React.ReactNode = (
		<>
			<SchemaSources />
			{originalSchema?.trim() && <Separator />}
			<SchemaEditor emptyMessage={schemaEmptyMessage} />
		</>
	);
	if (workspace === "releases") {
		workspaceActions = <ReleasesActions />;
		body = <ReleasesWorkspace />;
	}
	if (isLedger) {
		workspaceActions = <LedgerActions />;
		body = (
			<>
				<LedgerFileList />
				<LedgerOverview className={PANE_BOTTOM_PADDING} />
			</>
		);
	}

	return (
		<Pane
			className={className}
			position={position}
			collapsible={collapsible}
			isCollapsed={isCollapsed}
			onToggleCollapse={() => dispatch(toggleInputPane())}
		>
			<div className={"flex items-center justify-between gap-2 px-2 pt-2 pb-4"}>
				<div className={"flex items-center gap-2"}>
					<Select
						value={workspace}
						onValueChange={(value) => {
							dispatch(setWorkspace(value as Workspace));
						}}
					>
						<SelectTrigger aria-label={"Workspace"} title={"Workspace"}>
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							<SelectItem value={"schema"} disabled={isExploringRelease}>
								Schema
							</SelectItem>
							<SelectItem value={"releases"}>Releases</SelectItem>
							<SelectItem value={"ledger"}>Ledger</SelectItem>
						</SelectContent>
					</Select>
					<ThemeToggle />
				</div>
				{workspaceActions}
			</div>

			{body}
		</Pane>
	);
}
