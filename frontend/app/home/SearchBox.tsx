"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Search, MapPin, Star, Loader2 } from "lucide-react";
import sparklesSvg from "../assets/sparkles.svg";
import { searchRestaurants } from "./search";
import { useRestaurantStore } from "../store/useStore";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import styles from "./SearchBox.module.css";

interface Restaurant {
  name: string;
  address: string;
  place_id: string;
  rating?: number;
  user_ratings_total?: number;
}

const PRESET_RESTAURANTS: Restaurant[] = [
  {
    name: "Sweet Maple",
    address: "20010 Stevens Creek Blvd, Cupertino, CA 95014",
    place_id: "ChIJ45nohjW1j4ARlHArHtlS5I0",
    rating: 4.5,
    user_ratings_total: 988,
  },
  {
    name: "Marufuku Ramen Cupertino",
    address: "19772 Stevens Creek Blvd, Cupertino, CA 95014",
    place_id: "ChIJw1N0TPq1j4ARiWgSpsEurvo",
    rating: 4.4,
    user_ratings_total: 448,
  },
];

export default function SearchBox() {
  const router = useRouter();
  const reset = useRestaurantStore((s) => s.reset);
  const [query, setQuery] = useState("");
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [results, setResults] = useState<Restaurant[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search effect
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.length > 2 && !selectedRestaurant) {
        setIsLoading(true);
        setError(null);
        try {
          const data = await searchRestaurants(query);
          if (data.error) {
            setError(data.error);
          } else {
            const list = data.result || [];
            setResults(list);
          }
        } catch (err) {
          setError("Failed to fetch suggestions");
        } finally {
          setIsLoading(false);
        }
      } else {
        if (!selectedRestaurant) setResults([]);
        setIsLoading(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [query, selectedRestaurant]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (restaurant: Restaurant) => {
    setSelectedRestaurant(restaurant);
    setQuery(restaurant.name);
    setIsOpen(false);
  };

  const onClick = () => {
    if (selectedRestaurant) {
      if (selectedRestaurant.user_ratings_total && selectedRestaurant.user_ratings_total < 300) {
        alert("Because the review count is too small (< 300), we cannot process the summary for this restaurant.");
        return;
      }
      reset();
      const nameParam = selectedRestaurant.name ?? "";
      const processUrl = `/process?id=${selectedRestaurant.place_id}&reviews=${
        selectedRestaurant.user_ratings_total || 0
      }&name=${encodeURIComponent(nameParam)}`;
      router.push(processUrl);
    }
  };

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.tryThese}>
        <span className={styles.tryTheseLabel}>Try these:</span>
        {PRESET_RESTAURANTS.map((place) => (
          <Button
            key={place.place_id}
            variant="outline"
            size="sm"
            className={styles.tryTheseChip}
            onClick={() => handleSelect(place)}
          >
            <span className={styles.tryTheseName}>{place.name}</span>
            {place.rating != null && (
              <span className={styles.tryTheseRating}>
                <Star className={styles.iconSm} aria-hidden />
                {place.rating}
              </span>
            )}
          </Button>
        ))}
      </div>
      <div className={styles.inputWrapper}>
        <div className={styles.searchBar}>
          <Search className={styles.searchIcon} aria-hidden />
          <Input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (selectedRestaurant) setSelectedRestaurant(null);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search Restaurant"
            className={styles.inputInner}
          />
          {isLoading && <Loader2 className={styles.loader} aria-hidden />}
        </div>

        <AnimatePresence>
          {isOpen &&
            !selectedRestaurant &&
            (results.length > 0 || error || (query.length > 2 && !isLoading && results.length === 0)) && (
              <motion.div
                className={styles.dropdown}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.15 }}
              >
                <Card className={styles.dropdownCard}>
                  {error ? (
                    <div className={styles.error} role="alert">
                      {error}
                    </div>
                  ) : results.length > 0 ? (
                    <ul className={styles.list}>
                      {results.map((place) => (
                        <li key={place.place_id} className={styles.listItem}>
                          <Button variant="ghost" className={styles.suggestionItem} onClick={() => handleSelect(place)}>
                            <span className={styles.suggestionContent}>
                              <span className={styles.suggestionName}>{place.name}</span>
                              <span className={styles.suggestionMeta}>
                                <span className={styles.metaItem}>
                                  <MapPin className={styles.iconSm} aria-hidden />
                                  <span className={styles.addressText}>{place.address}</span>
                                </span>
                                {place.rating && (
                                  <span className={styles.ratingText}>
                                    <Star className={styles.iconSm} aria-hidden />
                                    {place.rating}
                                  </span>
                                )}
                              </span>
                            </span>
                          </Button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    query.length > 2 && !isLoading && <div className={styles.noResults}>No restaurants found.</div>
                  )}
                </Card>
              </motion.div>
            )}
        </AnimatePresence>
      </div>
      <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }} className={styles.buttonWrap}>
        <Button
          onClick={onClick}
          disabled={!selectedRestaurant}
          className={cn(styles.ctaButton, selectedRestaurant ? styles.ctaButtonEnabled : styles.ctaButtonDisabled)}
        >
          <Image src={sparklesSvg} alt="" width={16} height={16} className={styles.ctaButtonIcon} aria-hidden />
          Bring it to Life
        </Button>
      </motion.div>
    </div>
  );
}
