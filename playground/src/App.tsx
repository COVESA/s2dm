import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { Provider } from "react-redux";
import { ExplorePane } from "@/components/ExplorePane";
import { InputPane } from "@/components/InputPane";
import { ResultPane } from "@/components/ResultPane";
import { Heading } from "@/components/ui/heading";
import { appStartup } from "@/store/app/appSlice";
import { selectIsLoadingCapabilities } from "@/store/capabilities/capabilitiesSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { store } from "@/store/store";

declare module "react" {
	interface InputHTMLAttributes<T> extends HTMLAttributes<T> {
		webkitdirectory?: string;
	}
}

function AppContent() {
	const dispatch = useAppDispatch();
	const isLoadingCapabilities = useAppSelector(selectIsLoadingCapabilities);

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

	return (
		<div className="w-full h-screen p-4 flex flex-col">
			<div className="flex gap-4 flex-1 min-h-0 overflow-visible">
				<InputPane position="left" collapsible />

				<ExplorePane />

				<ResultPane position="right" collapsible />
			</div>
		</div>
	);
}

function App() {
	return (
		<Provider store={store}>
			<AppContent />
		</Provider>
	);
}

export default App;
