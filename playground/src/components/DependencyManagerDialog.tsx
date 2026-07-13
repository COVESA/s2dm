import { Eye, Plus, RefreshCw, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { DependenciesTab } from "@/components/dependencies/DependenciesTab";
import { DependencyStatusBadge } from "@/components/dependencies/DependencyStatusBadge";
import { IdentitiesTab } from "@/components/dependencies/IdentitiesTab";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
	fetchDependenciesConfig,
	fetchDependenciesStatus,
	selectDependencyStatus,
	selectDependencyStatusError,
	selectIsLoadingDependencyStatus,
} from "@/store/deps/depsSlice";
import { fetchIdentities } from "@/store/deps/identities/identitiesSlice";
import { selectIsResolvingDependencies } from "@/store/deps/resolve/resolveSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";

type DependencyManagerDialogProps = {
	open: boolean;
	onOpenChange: (open: boolean) => void;
};

type DependencyManagerTab = "dependencies" | "identities";

export function DependencyManagerDialog({
	open,
	onOpenChange,
}: DependencyManagerDialogProps) {
	const dispatch = useAppDispatch();
	const [activeTab, setActiveTab] =
		useState<DependencyManagerTab>("dependencies");
	const dependencyStatus = useAppSelector(selectDependencyStatus);
	const dependencyStatusError = useAppSelector(selectDependencyStatusError);
	const isDependencyStatusLoading = useAppSelector(
		selectIsLoadingDependencyStatus,
	);
	const isDependenciesResolving = useAppSelector(selectIsResolvingDependencies);

	const handleDialogOpenChange = useCallback(
		(isOpen: boolean) => {
			if (!isOpen) {
				setActiveTab("dependencies");
			}

			onOpenChange(isOpen);
		},
		[onOpenChange],
	);

	const handleDialogClose = useCallback(() => {
		handleDialogOpenChange(false);
	}, [handleDialogOpenChange]);

	useEffect(() => {
		if (!open) {
			return;
		}

		setActiveTab("dependencies");
		dispatch(fetchDependenciesStatus());
		dispatch(fetchDependenciesConfig());
		dispatch(fetchIdentities());
	}, [dispatch, open]);

	return (
		<Dialog open={open} onOpenChange={handleDialogOpenChange}>
			<DialogContent className="flex h-[50vh] w-[90vw] max-w-4xl flex-col sm:max-w-4xl">
				<Tabs
					value={activeTab}
					onValueChange={(value) => setActiveTab(value as DependencyManagerTab)}
					className="flex min-h-0 flex-1 flex-col"
				>
					<DialogHeader>
						<div className="space-y-3">
							<div className="flex items-center gap-4 pr-8">
								<div className="flex flex-wrap items-center gap-2">
									<DialogTitle>Manage Dependencies</DialogTitle>
									<DependencyStatusBadge
										status={dependencyStatus}
										isLoading={isDependencyStatusLoading}
										error={dependencyStatusError}
										isRefreshDisabled={isDependenciesResolving}
										onRefresh={() => dispatch(fetchDependenciesStatus())}
									/>
								</div>
							</div>
							<div className="flex items-center justify-center gap-2">
								<TabsList>
									<TabsTrigger value="dependencies">Dependencies</TabsTrigger>
									<TabsTrigger value="identities">Identities</TabsTrigger>
								</TabsList>
								<HelpButton
									title="Manage Dependencies"
									ariaLabel="Dependency manager help"
								>
									<HelpItem term="Status badge:">
										shows whether dependencies are configured, resolved, or out
										of date. Its{" "}
										<RefreshCw className="inline h-4 w-4 align-text-bottom" />{" "}
										refresh button re-checks the current status.
									</HelpItem>
									<HelpItem term="Dependencies / Identities tabs:">
										switch between managing dependency sources and the
										identities (host and scope) used to fetch private ones.
									</HelpItem>
									<HelpItem
										term={
											<>
												<Upload className="inline h-4 w-4 align-text-bottom" />{" "}
												Import
											</>
										}
									>
										load a dependencies or identities config from a file.
									</HelpItem>
									<HelpItem
										term={
											<>
												<Plus className="inline h-4 w-4 align-text-bottom" />{" "}
												Add
											</>
										}
									>
										create a new dependency or identity entry.
									</HelpItem>
									<HelpItem
										term={
											<>
												<Eye className="inline h-4 w-4 align-text-bottom" />{" "}
												View built schema
											</>
										}
									>
										preview the composed dependency schema.
									</HelpItem>
									<HelpItem term="Resolve">
										fetch and resolve the configured dependencies. The dropdown
										offers Clean and Resolve to discard cached results first.
									</HelpItem>
									<HelpItem term="Build">
										compose the resolved dependencies into a single schema. The
										dropdown offers Build and Auto-prefix.
									</HelpItem>
									<HelpItem term="Save">
										persist your dependency or identity changes.
									</HelpItem>
									<HelpItem term="Cancel">
										close the dialog without resolving or building.
									</HelpItem>
								</HelpButton>
							</div>
						</div>
					</DialogHeader>

					<DependenciesTab onDialogClose={handleDialogClose} />
					<IdentitiesTab onDialogClose={handleDialogClose} />
				</Tabs>
			</DialogContent>
		</Dialog>
	);
}
