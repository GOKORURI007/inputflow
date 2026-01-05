"""
An example script to test the CoordinateTransformer.
"""

from inputflow.config.manager import ConfigManager
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.core.logging import get_logger


def main():
    logger = get_logger("coordinates_example")
    config_manager = ConfigManager()

    # Load config to get display dimensions
    config = config_manager.load_config("config.toml.example")
    display_config = config.display

    logger.info(
        f"Loaded display dimensions: {display_config.width}x{display_config.height}"
    )

    # Initialize the transformer
    transformer = CoordinateTransformer(display_config.width, display_config.height)

    # --- Test Case 1: A point in the middle of the screen ---
    original_coords = (960, 540)
    logger.info(f"\n--- Testing with original coordinates: {original_coords} ---")

    # Normalize
    normalized_coords = transformer.normalize(original_coords[0], original_coords[1])
    logger.info(f"Normalized coordinates: {normalized_coords}")

    # Denormalize
    denormalized_coords = transformer.denormalize(
        normalized_coords[0], normalized_coords[1]
    )
    logger.info(f"Denormalized coordinates: {denormalized_coords}")

    assert original_coords == denormalized_coords
    logger.info("Round-trip conversion successful!")

    # --- Test Case 2: A point at the edge ---
    original_coords_edge = (display_config.width, display_config.height)
    logger.info(f"\n--- Testing with edge coordinates: {original_coords_edge} ---")

    normalized_coords_edge = transformer.normalize(
        original_coords_edge[0], original_coords_edge[1]
    )
    logger.info(f"Normalized coordinates (edge): {normalized_coords_edge}")

    denormalized_coords_edge = transformer.denormalize(
        normalized_coords_edge[0], normalized_coords_edge[1]
    )
    logger.info(f"Denormalized coordinates (edge): {denormalized_coords_edge}")

    assert original_coords_edge == denormalized_coords_edge
    logger.info("Round-trip conversion for edge case successful!")

    # --- Test Case 3: A point outside the bounds (should be clamped) ---
    original_coords_outside = (display_config.width + 100, -50)
    logger.info(
        f"\n--- Testing with outside coordinates: {original_coords_outside} ---"
    )

    normalized_coords_outside = transformer.normalize(
        original_coords_outside[0], original_coords_outside[1]
    )
    logger.info(f"Normalized coordinates (clamped): {normalized_coords_outside}")

    denormalized_coords_outside = transformer.denormalize(
        normalized_coords_outside[0], normalized_coords_outside[1]
    )
    logger.info(f"Denormalized coordinates (clamped): {denormalized_coords_outside}")

    assert denormalized_coords_outside == (display_config.width, 0)
    logger.info("Clamping for outside coordinates successful!")


if __name__ == "__main__":
    main()
