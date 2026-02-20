import { Label } from "@/components/ui/label";

interface FormLabelProps {
	htmlFor?: string;
	showRequired?: boolean;
	className?: string;
	children: React.ReactNode;
}

export function FormLabel({
	htmlFor,
	showRequired = false,
	className,
	children,
}: FormLabelProps) {
	return (
		<Label htmlFor={htmlFor} className={className}>
			{children}
			{showRequired && <span className="text-destructive ml-1">*</span>}
		</Label>
	);
}
