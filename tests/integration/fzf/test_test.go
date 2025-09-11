package fzf

import "testing"

// Broken tests

func TestBroken(t *testing.T) {
	t.Error("This test is supposed to fail.")
}

func TestSomethingElseBroken(t *testing.T) {
	t.Error("This test is also supposed to fail.")
}
