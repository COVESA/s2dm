import { StatusBanner } from "@shared-ui/components/status-banner";
import { useEffect, useState } from "react";
import { ComposeSection } from "@/components/ComposeSection";
import { ResolvedDependenciesSection } from "@/components/ResolvedDependenciesSection";
import { SourceFilesSection } from "@/components/SourceFilesSection";
import {
	fetchDependenciesConfig,
	fetchDependenciesStatus,
	selectHasResolvedDependencies,
} from "@/store/deps/depsSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectImportError } from "@/store/schema/schemaSlice";

type ListSection = "dependencies" | "files";

export function SchemaSources() {
	const dispatch = useAppDispatch();
	const hasResolvedDependencies = useAppSelector(selectHasResolvedDependencies);
	const importError = useAppSelector(selectImportError);
	const [openSection, setOpenSection] = useState<ListSection | null>("files");

	const handleCollapsedChange = (
		section: ListSection,
		isCollapsed: boolean,
	) => {
		if (isCollapsed) {
			setOpenSection(null);
			return;
		}
		setOpenSection(section);
	};

	let isFilesCollapsed = openSection !== "files";
	if (!hasResolvedDependencies && openSection === "dependencies") {
		isFilesCollapsed = false;
	}

	useEffect(() => {
		dispatch(fetchDependenciesStatus());
		dispatch(fetchDependenciesConfig());
	}, [dispatch]);

	return (
		<div className="flex min-h-0 flex-col">
			{importError && (
				<StatusBanner variant={"destructive"} className={"mx-2 mb-2"}>
					{importError}
				</StatusBanner>
			)}
			{hasResolvedDependencies && (
				<ResolvedDependenciesSection
					isCollapsed={openSection !== "dependencies"}
					onCollapsedChange={(isCollapsed) =>
						handleCollapsedChange("dependencies", isCollapsed)
					}
				/>
			)}
			<SourceFilesSection
				isCollapsed={isFilesCollapsed}
				onCollapsedChange={(isCollapsed) =>
					handleCollapsedChange("files", isCollapsed)
				}
			/>
			<ComposeSection />
		</div>
	);
}
