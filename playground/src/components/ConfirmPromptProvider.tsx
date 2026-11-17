import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useState,
} from "react";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const DEFAULT_TITLE = "Discard changes?";
const DEFAULT_CONFIRM_LABEL = "Discard";

/** An action that can lose data, with the text of the prompt that asks for it. */
export type ConfirmRequest = {
	/** Whether the action loses data. Without loss, the action runs at once. Defaults to true. */
	isDataLost?: boolean;
	/** The prompt title. Defaults to "Discard changes?". */
	title?: string;
	/** The sentence that names what is lost. */
	description: string;
	/** The label of the confirm button. Defaults to "Discard". */
	confirmLabel?: string;
	onConfirm: () => void;
};

type ConfirmAction = (request: ConfirmRequest) => void;

const ConfirmPromptContext = createContext<ConfirmAction | null>(null);

type ConfirmPromptProviderProps = {
	children: ReactNode;
};

/**
 * Shows one shared confirm prompt for the whole app. A request that loses no
 * data runs at once. A request that loses data runs only after the user
 * confirms it.
 *
 * @param children - The app content that sends confirm requests.
 * @returns The app content and the shared prompt.
 */
export function ConfirmPromptProvider({
	children,
}: ConfirmPromptProviderProps) {
	const [pendingRequest, setPendingRequest] = useState<ConfirmRequest | null>(
		null,
	);
	const [isPromptOpen, setIsPromptOpen] = useState(false);

	const confirmAction = useCallback((request: ConfirmRequest) => {
		const isDataLost = request.isDataLost ?? true;
		if (!isDataLost) {
			request.onConfirm();
			return;
		}

		setPendingRequest(request);
		setIsPromptOpen(true);
	}, []);

	const handleConfirm = () => {
		pendingRequest?.onConfirm();
	};

	const title = pendingRequest?.title ?? DEFAULT_TITLE;
	const description = pendingRequest?.description ?? "";
	const confirmLabel = pendingRequest?.confirmLabel ?? DEFAULT_CONFIRM_LABEL;

	return (
		<ConfirmPromptContext.Provider value={confirmAction}>
			{children}
			<AlertDialog open={isPromptOpen} onOpenChange={setIsPromptOpen}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>{title}</AlertDialogTitle>
						<AlertDialogDescription>{description}</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>Cancel</AlertDialogCancel>
						<AlertDialogAction onClick={handleConfirm} variant={"destructive"}>
							{confirmLabel}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</ConfirmPromptContext.Provider>
	);
}

/**
 * Gives the function that runs an action, or asks the user first when the
 * action loses data.
 *
 * @returns The function that takes a confirm request.
 */
export function useConfirmPrompt(): ConfirmAction {
	const confirmAction = useContext(ConfirmPromptContext);
	if (!confirmAction) {
		throw new Error("useConfirmPrompt needs a ConfirmPromptProvider.");
	}

	return confirmAction;
}
