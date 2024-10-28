import matplotlib.pyplot as plt

class MapVisualizer:
    """
        Клас MapVisualizer відповідає за візуалізацію геопросторових даних двома способами:

        1. **Графіки через Matplotlib**:
           Використовується для відображення кордону, сітки та секторів на одному статичному графіку.

    """
    def display_combined(self, border, grid, sectors, title="Combined Map"):
        """Відображає кордон, сітку квадратів та сектори на одному графіку."""
        fig, ax = plt.subplots(figsize=(10, 10))

        # Малюємо кордон України
        border.plot(ax=ax, edgecolor='black', facecolor='none', linewidth=2, zorder=3)

        # Малюємо сітку квадратів
        grid.plot(ax=ax, edgecolor='red', facecolor='none', alpha=0.5, zorder=1)

        # Малюємо сектори
        sectors.plot(ax=ax, edgecolor='blue', facecolor='none', alpha=0.5, zorder=2)

        plt.title(title)
        plt.xlabel("Довгота")
        plt.ylabel("Широта")

        plt.show()

