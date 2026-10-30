import { Minus, Plus, Repeat } from "lucide-react";
import { type ChangeEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const MIN_RECURSION_DEPTH = 0;
const DEPTH_PATTERN = /^\d+$/;

type RecursionDepthStepperProps = {
	value: number;
	onChange: (value: number) => void;
};

export function RecursionDepthStepper({
	value,
	onChange,
}: RecursionDepthStepperProps) {
	const [draft, setDraft] = useState(() => String(value));

	const commitValue = (nextValue: number) => {
		const nextDraft = String(nextValue);
		setDraft(nextDraft);
		onChange(nextValue);
	};

	const handleDraftChange = (event: ChangeEvent<HTMLInputElement>) => {
		const nextDraft = event.target.value;
		setDraft(nextDraft);
		if (!DEPTH_PATTERN.test(nextDraft)) {
			return;
		}

		const nextValue = Number.parseInt(nextDraft, 10);
		onChange(nextValue);
	};

	const handleBlur = () => {
		const committedDraft = String(value);
		setDraft(committedDraft);
	};

	return (
		<div
			className={"flex items-center gap-1"}
			title={"Cycle depth: how many cyclic fields deep the tree can expand"}
		>
			<Repeat className={"size-3.5 text-muted-foreground"} />
			<Button
				type={"button"}
				variant={"outline"}
				size={"icon-xs"}
				onClick={() => commitValue(value - 1)}
				disabled={value <= MIN_RECURSION_DEPTH}
				aria-label={"Decrease cycle depth"}
			>
				<Minus />
			</Button>
			<Input
				type={"text"}
				inputMode={"numeric"}
				value={draft}
				onChange={handleDraftChange}
				onBlur={handleBlur}
				aria-label={"Cycle depth"}
				className={"h-6 w-9 px-1 text-center"}
			/>
			<Button
				type={"button"}
				variant={"outline"}
				size={"icon-xs"}
				onClick={() => commitValue(value + 1)}
				aria-label={"Increase cycle depth"}
			>
				<Plus />
			</Button>
		</div>
	);
}
