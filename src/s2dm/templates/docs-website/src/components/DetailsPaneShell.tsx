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
 * sit in the document flow beneath the workspace, where there is no pane to
 * close and the page's own scroll position is the way back — so the title and
 * both controls are left out and only the body is rendered.
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
