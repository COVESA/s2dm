type HighlightedTextProps = {
	text: string;
	normalizedTerm: string;
};

export function HighlightedText({
	text,
	normalizedTerm,
}: HighlightedTextProps) {
	const lowerCaseText = text.toLowerCase();
	const matchStart = lowerCaseText.indexOf(normalizedTerm);
	if (!normalizedTerm || matchStart === -1) {
		return text;
	}

	const matchEnd = matchStart + normalizedTerm.length;
	return (
		<>
			{text.slice(0, matchStart)}
			<mark className={"rounded-sm bg-primary/20 text-foreground"}>
				{text.slice(matchStart, matchEnd)}
			</mark>
			{text.slice(matchEnd)}
		</>
	);
}
