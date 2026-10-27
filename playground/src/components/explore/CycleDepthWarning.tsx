import { EvidenceRow } from "@insights-ui/components/EvidenceRow";
import { PagedList } from "@insights-ui/components/PagedList";
import { TypePathBreadcrumb } from "@insights-ui/components/TypePathBreadcrumb";
import { Button } from "@shared-ui/components/button";
import { TriangleAlert } from "lucide-react";
import { useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

type CycleDepthWarningProps = {
	/** Each path as its segment keys from the root. */
	paths: string[][];
	maxRecursionDepth: number;
	className?: string;
};

export function CycleDepthWarning({
	paths,
	maxRecursionDepth,
	className,
}: CycleDepthWarningProps) {
	const [isOpen, setIsOpen] = useState(false);

	return (
		<>
			<Button
				type={"button"}
				variant={"outline"}
				size={"icon"}
				className={className}
				onClick={() => setIsOpen(true)}
				aria-label={"Show cycle depth warning"}
				title={"The selection goes deeper than the cycle depth"}
			>
				<TriangleAlert className={"text-amber-600 dark:text-amber-400"} />
			</Button>
			<Dialog open={isOpen} onOpenChange={setIsOpen}>
				<DialogContent className={"sm:max-w-lg"}>
					<DialogHeader>
						<DialogTitle>Deeper than the cycle depth</DialogTitle>
						<DialogDescription>
							These selected paths pass through more cyclic fields than the
							cycle depth of {maxRecursionDepth} allows. Applying keeps them as
							written. To match the tree, remove them or raise the cycle depth.
						</DialogDescription>
					</DialogHeader>
					<div className={"max-h-80 overflow-y-auto"}>
						<PagedList
							items={paths}
							getKey={(segments) => segments.join("/")}
							renderItem={(segments) => (
								<li>
									<EvidenceRow>
										<div className={"min-w-0 overflow-x-auto"}>
											<TypePathBreadcrumb segments={segments} scrollable />
										</div>
									</EvidenceRow>
								</li>
							)}
						/>
					</div>
				</DialogContent>
			</Dialog>
		</>
	);
}
