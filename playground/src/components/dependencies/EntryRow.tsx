import { ChevronRight, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

type EntryRowProps = {
	primary: string;
	secondary?: string;
	onEdit: () => void;
	onRemove: () => void;
	removeTitle: string;
};

export function EntryRow({
	primary,
	secondary,
	onEdit,
	onRemove,
	removeTitle,
}: EntryRowProps) {
	return (
		<div className="rounded-md border bg-background/50 transition-colors hover:bg-background/80">
			<div className="flex items-center gap-1">
				<Button
					type="button"
					variant="ghost"
					onClick={onEdit}
					className="h-10 flex-1 justify-between rounded-r-none px-3 text-left hover:bg-transparent"
				>
					<span className="flex min-w-0 flex-1 items-center text-sm font-medium text-foreground">
						<span className="truncate">{primary}</span>
						{secondary && (
							<>
								<span className="px-2 text-muted-foreground">|</span>
								<span className="truncate text-muted-foreground">
									{secondary}
								</span>
							</>
						)}
					</span>
					<span className="text-muted-foreground">
						<ChevronRight className="h-4 w-4" />
					</span>
				</Button>
				<Button
					type="button"
					variant="ghost"
					size="icon-sm"
					onClick={(event) => {
						event.stopPropagation();
						onRemove();
					}}
					className="mr-2 text-destructive hover:bg-destructive/10 hover:text-destructive"
					title={removeTitle}
				>
					<Trash2 />
				</Button>
			</div>
		</div>
	);
}
