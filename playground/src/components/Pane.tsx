import {
	PanelLeftClose,
	PanelLeftOpen,
	PanelRightClose,
	PanelRightOpen,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PaneProps = {
	children: React.ReactNode;
	className?: string;
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	isCollapsed?: boolean;
	onToggleCollapse?: () => void;
	shadow?: boolean;
};

export function Pane({
	children,
	className,
	position = "none",
	collapsible = false,
	isCollapsed,
	onToggleCollapse,
	shadow = true,
}: PaneProps) {
	const showCollapseButton =
		collapsible && (position === "left" || position === "right");
	const [localCollapsed, setLocalCollapsed] = useState(false);

	const collapsed = isCollapsed ?? localCollapsed;
	const handleToggle =
		onToggleCollapse ?? (() => setLocalCollapsed((prev) => !prev));

	useEffect(() => {
		if (!collapsible) return;

		const handleKeyPress = (e: KeyboardEvent) => {
			const target = e.target as HTMLElement;
			if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
				return;
			}

			if (position === "left" && e.key === "/") {
				e.preventDefault();
				handleToggle();
			} else if (position === "right" && e.key === "\\") {
				e.preventDefault();
				handleToggle();
			}
		};

		window.addEventListener("keydown", handleKeyPress);
		return () => window.removeEventListener("keydown", handleKeyPress);
	}, [collapsible, position, handleToggle]);

	const getCollapseIcon = () => {
		if (position === "left") {
			if (collapsed) {
				return <PanelLeftOpen className="h-4 w-4" />;
			}
			return <PanelLeftClose className="h-4 w-4" />;
		}
		if (position === "right") {
			if (collapsed) {
				return <PanelRightOpen className="h-4 w-4" />;
			}
			return <PanelRightClose className="h-4 w-4" />;
		}
		return null;
	};

	const getButtonPosition = () => {
		if (position === "left") {
			return "bottom-2 right-2";
		}
		if (position === "right") {
			return "bottom-2 left-2";
		}
		return "";
	};

	const getWidthClass = () => {
		if (position === "left" || position === "right") {
			return collapsed ? "w-12" : "w-[25%]";
		}
		return "";
	};

	return (
		<div
			className={cn(
				"group/pane flex flex-col min-w-0 relative transition-all duration-300 rounded-lg",
				shadow && "shadow-pane",
				getWidthClass(),
				className,
			)}
		>
			<div
				className={cn(
					"flex flex-col flex-1 min-h-0 rounded-lg overflow-hidden",
					collapsed && "hidden",
				)}
			>
				{children}
			</div>

			{showCollapseButton && (
				<Button
					variant="outline"
					size="icon"
					className={cn(
						"absolute z-10 !bg-background hover:!bg-muted transition-opacity",
						collapsed
							? "opacity-100"
							: "opacity-0 group-hover/pane:opacity-100",
						getButtonPosition(),
					)}
					onClick={handleToggle}
					title={collapsed ? "Expand" : "Collapse"}
				>
					{getCollapseIcon()}
				</Button>
			)}
		</div>
	);
}
