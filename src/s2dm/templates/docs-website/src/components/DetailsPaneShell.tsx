type DetailsPaneShellProps = {
	title: string;
	onClose: () => void;
	onBack?: () => void;
	trailing?: React.ReactNode;
	bodyKey?: string;
	children: React.ReactNode;
};

/**
 * The details body, as this site lays it out.
 *
 * The playground shows details in a collapsible pane beside the content, with a
 * header carrying the record title, a back arrow and a close button. Here they
 * sit in the document flow beneath the workspace, so the header is left out and
 * only the body is rendered.
 *
 * That makes the detail stack one-way: following a chain node or an action
 * pushes onto it with nothing to pop it, and the only way out is selecting
 * another record. Deliberate — the controls were not wanted on this host — so
 * `title`, `onBack` and `onClose` are accepted to keep the shared contract and
 * then ignored.
 */
export function DetailsPaneShell({ bodyKey, children }: DetailsPaneShellProps) {
	return (
		<div
			key={bodyKey}
			className="animate-in px-5 pt-5 pb-8 fade-in duration-200"
		>
			{children}
		</div>
	);
}
