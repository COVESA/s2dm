import { InsightsHostDefaults } from "@insights-ui/hostDefaults";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { Provider } from "react-redux";
import { ExplorePane } from "@/components/ExplorePane";
import { InputPane } from "@/components/InputPane";
import { InsightsDetailsPane } from "@/components/InsightsDetailsPane";
import { LedgerDetailsPane } from "@/components/ledger/LedgerDetailsPane";
import { ResultPane } from "@/components/ResultPane";
import { Heading } from "@/components/ui/heading";
import { appStartup } from "@/store/app/appSlice";
import { selectIsLoadingCapabilities } from "@/store/capabilities/capabilitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { store } from "@/store/store";
import { selectExploreTab, selectWorkspace } from "@/store/ui/uiSlice";

declare module "react" {
	interface InputHTMLAttributes<T> extends HTMLAttributes<T> {
		webkitdirectory?: string;
	}
}

function AppContent() {
	const dispatch = useAppDispatch();
	const isLoadingCapabilities = useAppSelector(selectIsLoadingCapabilities);
	const workspace = useAppSelector(selectWorkspace);
	const exploreTab = useAppSelector(selectExploreTab);

	useEffect(() => {
		dispatch(appStartup());
	}, [dispatch]);

	if (isLoadingCapabilities) {
		return (
			<div className="w-full h-screen flex flex-col items-center justify-center gap-4">
				<Heading level="h1">S2DM Playground</Heading>
				<Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

	let rightPane = <ResultPane position="right" collapsible />;
	if (workspace === "ledger") {
		rightPane = <LedgerDetailsPane position="right" collapsible />;
	} else if (exploreTab === "insights") {
		rightPane = <InsightsDetailsPane position="right" collapsible />;
	}

	return (
		<div className="w-full h-screen p-4 flex flex-col">
			<div className="flex gap-4 flex-1 min-h-0 overflow-visible">
				<InputPane position="left" collapsible />

				<ExplorePane />

				{rightPane}
			</div>
		</div>
	);
}

function App() {
	return (
		<Provider store={store}>
			<InsightsHostDefaults selectableCards>
				<AppContent />
			</InsightsHostDefaults>
		</Provider>
	);
}

export default App;
