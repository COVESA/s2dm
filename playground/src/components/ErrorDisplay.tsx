import { Heading } from "@/components/ui/heading";

type ErrorDisplayProps = {
	error: string;
};

export function ErrorDisplay({ error }: ErrorDisplayProps) {
	return (
		<div className="flex-1 flex flex-col p-4 bg-destructive/10 rounded-lg border border-destructive overflow-hidden">
			<Heading level="h3" className="text-destructive mb-4">
				Error:
			</Heading>
			<pre className="flex-1 overflow-auto p-4 bg-destructive/5 rounded text-sm">
				{error}
			</pre>
		</div>
	);
}
