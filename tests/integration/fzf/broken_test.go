// Copyright (C) 2026 Maxwell G <maxwell@gtmx.me>
// SPDX-License-Identifier: MIT

//go:build brokendir

package brokendir

import "testing"

func TestBrokenDir(t *testing.T) {
	t.Error("This test should fail when -tag brokendir is passed")

