import { useEffect } from "react";
import { ComposeSection } from "@/components/ComposeSection";
import { FileListHeader } from "@/components/FileListHeader";
import { ResolvedDependenciesSection } from "@/components/ResolvedDependenciesSection";
import { SourceFilesSection } from "@/components/SourceFilesSection";
import {
	fetchDependenciesConfig,
	fetchDependenciesStatus,
} from "@/store/deps/depsSlice";
import { useAppDispatch } from "@/store/hooks";

export function FileList() {
	const dispatch = useAppDispatch();

	useEffect(() => {
		dispatch(fetchDependenciesStatus());
		dispatch(fetchDependenciesConfig());
	}, [dispatch]);

	return (
		<div className="flex flex-col">
			<FileListHeader />
			<ResolvedDependenciesSection />
			<SourceFilesSection />
			<ComposeSection />
		</div>
	);
}
