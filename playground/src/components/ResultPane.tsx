import { useCallback, useEffect, useState } from "react";
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
	selectCapabilitiesError,
	selectExporters,
	selectIsLoadingCapabilities,
} from "@/store/capabilities/capabilitiesSlice";
import {
	clearExportResult,
	exportSchema,
	selectExportError,
	selectExportFormat,
	selectExportResult,
	selectIsExporting,
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
	const isExporting = useAppSelector(selectIsExporting);
	const exportResult = useAppSelector(selectExportResult);
	const exportError = useAppSelector(selectExportError);
	const exportFormat = useAppSelector(selectExportFormat);
	const exporters = useAppSelector(selectExporters);
	const isLoadingCapabilities = useAppSelector(selectIsLoadingCapabilities);
	const capabilitiesError = useAppSelector(selectCapabilitiesError);
	const [selectedExporter, setSelectedExporter] = useState<string>(
		exporters[0]?.name || "",
	);

	useEffect(() => {
		if (exporters.length > 0 && !selectedExporter) {
			setSelectedExporter(exporters[0].name);
		}
	}, [exporters, selectedExporter]);

	const handleGenerate = useCallback(() => {
		const selectedExporterData = exporters.find(
			(exp) => exp.name === selectedExporter,
		);
		if (!selectedExporterData) {
			return;
		}

		dispatch(
			exportSchema({
				endpoint: selectedExporterData.endpoint,
			}),
		);
	}, [selectedExporter, dispatch, exporters]);

	const handleReset = useCallback(() => {
		dispatch(clearExportResult());
	}, [dispatch]);

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
			collapsible={collapsible}
			isCollapsed={isCollapsed}
			onToggleCollapse={() => dispatch(toggleResultPane())}
		>
			<div className="flex gap-2 p-4 items-center justify-center">
				<Select value={selectedExporter} onValueChange={setSelectedExporter}>
					<SelectTrigger className="w-[200px]">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{exporters.map((exporter) => (
							<SelectItem key={exporter.name} value={exporter.name}>
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
				<CliCommandDisplay type="export" selectedExporter={selectedExporter} />
			</div>

			<ExportConfig selectedExporter={selectedExporter} />

			{exportResult && <Separator />}

			{renderContent()}
		</Pane>
	);
}
