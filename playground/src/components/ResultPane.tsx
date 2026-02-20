import { useCallback } from "react";
import { CliCommandDisplay } from "@/components/CliCommandDisplay";
import { ErrorDisplay } from "@/components/ErrorDisplay";
import { ExportConfig } from "@/components/ExportConfig";
import { Pane } from "@/components/Pane";
import { TextEditor } from "@/components/TextEditor";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
	fetchCapabilities,
	setSelectedExporterEndpoint,
	selectCapabilitiesError,
	selectSelectedExporterEndpoint,
	selectExporterByEndpoint,
	selectExporters,
	selectIsLoadingCapabilities,
} from "@/store/capabilities/capabilitiesSlice";
import {
	clearExportResult,
	clearExportResultForEndpoint,
	exportSchema,
	selectExportError,
	selectExportFormat,
	selectExportResult,
	selectIsExportingEndpoint,
} from "@/store/export/exportSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectFilteredSchema } from "@/store/schema/schemaSlice";
import {
	selectResultPaneCollapsed,
	toggleResultPane,
} from "@/store/ui/uiSlice";

type ResultPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function ResultPane({
	position,
	collapsible,
	className = "bg-card",
}: ResultPaneProps) {
	const dispatch = useAppDispatch();
	const isCollapsed = useAppSelector(selectResultPaneCollapsed);
	const filteredSchema = useAppSelector(selectFilteredSchema);
	const hasFilteredSchema = filteredSchema.trim().length > 0;
	const canCollapsePane = Boolean(collapsible && hasFilteredSchema);
	const shouldCollapsePane = !hasFilteredSchema || isCollapsed;
	const exporters = useAppSelector(selectExporters);
	const selectedExporterEndpoint = useAppSelector(
		selectSelectedExporterEndpoint,
	);
	const selectedExporterData = useAppSelector((state) =>
		selectExporterByEndpoint(state, selectedExporterEndpoint),
	);
	const selectedEndpoint = selectedExporterData?.endpoint || "";
	const isExporting = useAppSelector((state) =>
		selectedEndpoint
			? selectIsExportingEndpoint(state, selectedEndpoint)
			: false,
	);
	const exportResult = useAppSelector((state) =>
		selectedEndpoint ? selectExportResult(state, selectedEndpoint) : "",
	);
	const exportError = useAppSelector((state) =>
		selectedEndpoint ? selectExportError(state, selectedEndpoint) : null,
	);
	const exportFormat = useAppSelector((state) =>
		selectedEndpoint ? selectExportFormat(state, selectedEndpoint) : "text",
	);
	const isLoadingCapabilities = useAppSelector(selectIsLoadingCapabilities);
	const capabilitiesError = useAppSelector(selectCapabilitiesError);

	const handleGenerate = useCallback(() => {
		if (!selectedExporterData) {
			return;
		}

		dispatch(
			exportSchema({
				endpoint: selectedExporterData.endpoint,
			}),
		);
	}, [selectedExporterData, dispatch]);

	const handleReset = useCallback(() => {
		if (!selectedEndpoint) {
			dispatch(clearExportResult());
			return;
		}

		dispatch(clearExportResultForEndpoint(selectedEndpoint));
	}, [dispatch, selectedEndpoint]);

	const handleRetryCapabilities = useCallback(() => {
		dispatch(fetchCapabilities());
	}, [dispatch]);

	const renderContent = () => {
		if (capabilitiesError) {
			return (
				<EmptyState>
					<ErrorDisplay error={capabilitiesError} />
					<Button onClick={handleRetryCapabilities}>Retry</Button>
				</EmptyState>
			);
		}

		if (isLoadingCapabilities) {
			return <EmptyState isLoading />;
		}

		if (exportError) {
			return <ErrorDisplay error={exportError} />;
		}

		if (isExporting) {
			return <EmptyState isLoading title="Exporting..." />;
		}

		if (exportResult) {
			return (
				<div className="flex-1 min-h-0">
					<TextEditor
						language={exportFormat}
						value={exportResult}
						readOnly
						fullscreenTitle="Export"
						fileName={exportFormat ? `output.${exportFormat}` : undefined}
					/>
				</div>
			);
		}

		return <EmptyState title="Nothing to display" />;
	};

	return (
		<Pane
			className={className}
			position={position}
			collapsible={canCollapsePane}
			isCollapsed={shouldCollapsePane}
			onToggleCollapse={
				canCollapsePane ? () => dispatch(toggleResultPane()) : undefined
			}
		>
			<div className="flex gap-2 p-4 items-center justify-center">
				<Select
					value={selectedExporterEndpoint}
					onValueChange={(value) =>
						dispatch(setSelectedExporterEndpoint(value))
					}
				>
					<SelectTrigger className="w-[200px]">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{exporters.map((exporter) => (
							<SelectItem key={exporter.endpoint} value={exporter.endpoint}>
								{exporter.name}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				<Button
					onClick={handleGenerate}
					disabled={!filteredSchema?.trim()}
					loading={isExporting}
				>
					Export
				</Button>
				<Button
					variant="destructive"
					onClick={handleReset}
					disabled={!exportResult && !exportError}
					title="Reset output"
				>
					Reset
				</Button>
			</div>

			<div className="px-4 pb-4">
				<CliCommandDisplay
					type="export"
					selectedExporterEndpoint={selectedExporterEndpoint}
				/>
			</div>

			<ExportConfig selectedExporterEndpoint={selectedExporterEndpoint} />

			{exportResult && <Separator />}

			{renderContent()}
		</Pane>
	);
}
