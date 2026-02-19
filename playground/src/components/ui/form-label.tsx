import { Label } from "@/components/ui/label";

interface FormLabelProps {
	htmlFor: string;
	showRequired?: boolean;
	children: React.ReactNode;
}

export function FormLabel({
	htmlFor,
	showRequired = false,
	children,
}: FormLabelProps) {
	return (
		<Label htmlFor={htmlFor}>
			{children}
			{showRequired && <span className="text-destructive ml-1">*</span>}
		</Label>
	);
}
